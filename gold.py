CHUNK_SIZE = 1200
OVERLAP    = 150

def chunk_words(text: str, size: int = CHUNK_SIZE, overlap: int = OVERLAP):
    if not text:
        return []
    words = text.split()
    out = []
    i = 0
    while i < len(words):
        out.append(" ".join(words[i:i+size]))
        i += max(1, (size - overlap))
    return out

chunk_udf = F.udf(lambda s: chunk_words(s, CHUNK_SIZE, OVERLAP), T.ArrayType(T.StringType()))


########################################Gold image items (rendered pages + embedded)######################################

silver_imgs = spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_images")

gold_pdf_image_items = (
    silver_imgs
      .withColumn("id", F.sha2(F.concat_ws("||",
                                           F.col("doc_id"),
                                           F.col("page_num").cast("string"),
                                           F.lit("image"),
                                           F.col("image_id")), 256))
      .withColumn("item_type", F.lit("image"))
      .withColumn("content", F.lit(None).cast("string"))
      .select(
          "id","doc_id","file_name","page_num","item_type",
          "content",
          F.col("image_url").alias("image_url"),
          F.col("pdf_url").alias("pdf_url"),
          "image_kind","image_id","image_abfss_path"
      )
)

(gold_pdf_image_items.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_pdf_image_items"))

display(spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_image_items").limit(10))



###############################Optional unified Gold table (requested)###################################################


gold_text = spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_text_chunks") \
    .select("id","doc_id","page_num","item_type","content", F.lit(None).cast("string").alias("image_url"), "pdf_url")

gold_img  = spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_image_items") \
    .select("id","doc_id","page_num","item_type","content","image_url","pdf_url")

gold_pdf_items_unified = gold_text.unionByName(gold_img)

(gold_pdf_items_unified.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_pdf_items_unified"))

display(spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_items_unified").limit(20))

