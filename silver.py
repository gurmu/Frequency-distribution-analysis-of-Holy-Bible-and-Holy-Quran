silver_pdf_pages = (
    spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_pages").alias("p")
    .join(
        spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_bin").select("doc_id","path","file_name").alias("b"),
        on="doc_id",
        how="left"
    )
    .withColumn("pdf_url", abfss_to_https_udf(F.col("path")))
    .withColumn("page_text_clean",
                F.trim(F.regexp_replace(F.col("page_text_raw"), r"\s+", " ")))
)

(silver_pdf_pages.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_pdf_pages"))


#################################persist images to itsmimages container (and store URLs)############################################


silver_pdf_images = (
    spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_images").alias("i")
    .join(
        spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_bin").select("doc_id","path").alias("b"),
        on="doc_id",
        how="left"
    )
    .withColumn("pdf_url", abfss_to_https_udf(F.col("path")))
)

# Build target ABFSS paths
def infer_ext(name: str, default="png"):
    if not name:
        return default
    m = re.search(r"\.([A-Za-z0-9]+)$", name)
    return (m.group(1).lower() if m else default)

infer_ext_udf = F.udf(infer_ext, T.StringType())

silver_pdf_images = (
    silver_pdf_images
      .withColumn("ext", infer_ext_udf(F.col("image_name")))
      .withColumn(
          "image_abfss_path",
          F.when(
              F.col("image_kind") == F.lit("page_render"),
              F.concat(F.lit(IMG_ROOT), F.col("doc_id"), F.lit("/page_"),
                       F.lpad(F.col("page_num").cast("string"), 4, "0"),
                       F.lit(".png"))
          ).otherwise(
              F.concat(F.lit(IMG_ROOT), F.col("doc_id"), F.lit("/embedded/p"),
                       F.lpad(F.col("page_num").cast("string"), 4, "0"),
                       F.lit("_"), F.col("image_id"), F.lit("."), F.col("ext"))
          )
      )
      .withColumn("image_url", abfss_to_https_udf(F.col("image_abfss_path")))
      .drop("ext")
)

(silver_pdf_images.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_pdf_images"))



##########################################Build silver_pdf_images (paths + https links)#####################################

# DRIVER-SAFE binary write to ABFSS using Hadoop FileSystem
jvm  = spark._jvm
conf = spark._jsc.hadoopConfiguration()
fs   = jvm.org.apache.hadoop.fs.FileSystem.get(conf)
Path = jvm.org.apache.hadoop.fs.Path

def write_one_binary(abfss_path: str, b: bytes, overwrite: bool = True):
    p = Path(abfss_path)
    if overwrite and fs.exists(p):
        fs.delete(p, True)
    out = fs.create(p, True)  # overwrite
    out.write(bytearray(b))
    out.close()

# Stream rows (no collect), write only what doesn't exist if you want
to_write = spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_images") \
               .select("image_abfss_path","image_bytes") \
               .toLocalIterator()

count = 0
for r in to_write:
    if r["image_bytes"] is None:
        continue
    write_one_binary(r["image_abfss_path"], r["image_bytes"], overwrite=True)
    count += 1
    if count % 200 == 0:
        print("Wrote images:", count)

print("DONE. Total images written:", count)

