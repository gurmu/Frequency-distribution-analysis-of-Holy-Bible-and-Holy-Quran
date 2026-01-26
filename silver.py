silver_pdf_pages = (
    spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_pages").alias("p")
      .join(
          spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_bin").select("doc_id","path","file_name").alias("b"),
          on="doc_id",
          how="left"
      )
      .withColumn("pdf_url", abfss_to_https_udf(F.col("path")))
      .withColumn("page_text_clean", F.trim(F.regexp_replace(F.col("page_text_raw"), r"\s+", " ")))
      .drop("page_text_raw")
)

(silver_pdf_pages.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_pdf_pages"))

display(spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_pages").limit(10))

#################################persist images to itsmimages container (and store URLs)############################################


from pyspark.sql import Row

def write_images_partition(rows):
    """
    rows: iterator of Row(doc_id,page_num,image_id,image_kind,image_name,image_mime,image_bytes,...)
    """
    jvm = spark._jvm
    conf = spark._jsc.hadoopConfiguration()
    fs = jvm.org.apache.hadoop.fs.FileSystem.get(conf)

    for r in rows:
        doc_id    = r["doc_id"]
        page_num  = int(r["page_num"])
        image_id  = r["image_id"]
        kind      = r["image_kind"]
        name      = r["image_name"]
        b         = r["image_bytes"]

        if b is None:
            continue

        # Choose extension from name (fallback png)
        ext = "png"
        m = re.search(r"\.([a-zA-Z0-9]+)$", name or "")
        if m:
            ext = m.group(1).lower()

        if kind == "page_render":
            # enforce standard page naming
            out_key = f"{doc_id}/page_render/page_{page_num:04d}.png"
        else:
            out_key = f"{doc_id}/embedded/p{page_num:04d}_{image_id}.{ext}"

        out_abfss = IMG_ROOT + out_key  # IMG_ROOT already ends with '/'

        path = jvm.org.apache.hadoop.fs.Path(out_abfss)
        # idempotent: overwrite if exists
        stream = fs.create(path, True)

        # write bytes
        stream.write(bytearray(b))
        stream.close()

# Execute the distributed write
bronze_img_df = spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_images")
bronze_img_df.rdd.foreachPartition(write_images_partition)


##########################################Build silver_pdf_images (paths + https links)#####################################

silver_pdf_images = (
    spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_images").alias("i")
      .join(
          spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_bin").select("doc_id","path","file_name").alias("b"),
          on="doc_id",
          how="left"
      )
      .withColumn("pdf_url", abfss_to_https_udf(F.col("path")))
      .withColumn(
          "image_abfss_path",
          F.when(
              F.col("image_kind") == F.lit("page_render"),
              F.concat(F.lit(IMG_ROOT), F.col("doc_id"), F.lit("/page_render/page_"),
                       F.lpad(F.col("page_num").cast("string"), 4, "0"), F.lit(".png"))
          ).otherwise(
              F.concat(F.lit(IMG_ROOT), F.col("doc_id"), F.lit("/embedded/p"),
                       F.lpad(F.col("page_num").cast("string"), 4, "0"),
                       F.lit("_"), F.col("image_id"), F.lit("."),
                       F.regexp_extract(F.col("image_name"), r"\.([A-Za-z0-9]+)$", 1))
          )
      )
      .withColumn("image_url", abfss_to_https_udf(F.col("image_abfss_path")))
      # optional: drop bytes in silver to avoid large storage
      .drop("image_bytes")
)

(silver_pdf_images.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_pdf_images"))

display(spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_images").limit(10))
