def clean_text(s: str) -> str:
    if not s:
        return None
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None

clean_text_udf = F.udf(lambda x: clean_text(x), T.StringType())

silver_pages = (
    spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_pages")
      .join(
          spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_bin").select("doc_id", "path", "file_name"),
          on="doc_id",
          how="left"
      )
      .withColumn("page_text_clean", clean_text_udf(F.col("page_text_raw")))
      .withColumn("pdf_abfss_path", F.col("path"))
      .withColumn("pdf_url", F.udf(abfss_to_https, T.StringType())(F.col("path")))
      .select("doc_id", "file_name", "page_num", "page_text_clean", "pdf_abfss_path", "pdf_url")
)

(silver_pages.write.mode("overwrite")
 .option("mergeSchema", "true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_pdf_pages"))

#################################persist images to itsmimages container (and store URLs)############################################


import os, tempfile

def write_bytes_to_abfss(abfss_path: str, b: bytes):
    """
    Write bytes to ABFSS by writing a local temp file then copying.
    """
    if not abfss_path or b is None:
        return
    local_dir = "/dbfs/tmp/pdf_mm"
    os.makedirs(local_dir, exist_ok=True)

    # unique local temp name
    local_path = os.path.join(local_dir, sha256_str(abfss_path) + ".bin")
    with open(local_path, "wb") as f:
        f.write(b)

    # copy to target
    dbutils.fs.cp("file:" + local_path, abfss_path, True)

def get_ext_from_mime(mime: str, fallback="bin"):
    if mime == "image/png":
        return "png"
    if mime == "image/jpeg":
        return "jpg"
    return fallback

# We'll create a Pandas UDF to write images and return their paths.
out_schema = T.StructType([
    T.StructField("doc_id", T.StringType()),
    T.StructField("page_num", T.IntegerType()),
    T.StructField("image_id", T.StringType()),
    T.StructField("image_kind", T.StringType()),
    T.StructField("image_abfss_path", T.StringType()),
    T.StructField("image_url", T.StringType()),
])

def persist_images_map(pdf_iter):
    for batch in pdf_iter:
        out = []
        for _, r in batch.iterrows():
            doc_id = r["doc_id"]
            page_num = int(r["page_num"])
            image_id = r["image_id"]
            image_kind = r["image_kind"]
            mime = r["image_mime"]
            b = r["image_bytes"]

            ext = get_ext_from_mime(mime, "bin")

            if image_kind == "page_render":
                # deterministic rendered page name
                rel = f"{doc_id}/page_{page_num:04d}.png"
            else:
                # embedded
                rel = f"{doc_id}/embedded/p{page_num:04d}_{image_id}.{ext}"

            image_abfss = f"{IMG_BASE_DIR}/{rel}"
            try:
                write_bytes_to_abfss(image_abfss, b)
                image_https = abfss_to_https(image_abfss)
            except Exception:
                image_https = None  # don't fail the whole batch

            out.append({
                "doc_id": doc_id,
                "page_num": page_num,
                "image_id": image_id,
                "image_kind": image_kind,
                "image_abfss_path": image_abfss,
                "image_url": image_https
            })
        yield pd.DataFrame(out)

bronze_img_df = spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_images").select(
    "doc_id", "page_num", "image_id", "image_kind", "image_mime", "image_bytes"
)

silver_images = bronze_img_df.mapInPandas(persist_images_map, schema=out_schema)

(silver_images.write.mode("overwrite")
 .option("mergeSchema", "true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_pdf_images"))
