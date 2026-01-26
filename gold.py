def chunk_text(s: str, max_len: int = 1200, overlap: int = 150):
    s = s or ""
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return []
    chunks = []
    start = 0
    n = len(s)
    while start < n:
        end = min(start + max_len, n)
        chunk = s[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

chunk_text_udf = F.udf(lambda s: chunk_text(s, 1200, 150), T.ArrayType(T.StringType()))

gold_pdf_text_chunks = (
    spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_pages")
      .withColumn("chunks", chunk_text_udf(F.col("page_text_clean")))
      .withColumn("chunk_index_and_text", F.posexplode(F.col("chunks")))
      .select(
          F.col("doc_id"),
          F.col("page_num"),
          F.col("file_name"),
          F.col("pdf_url"),
          F.col("chunk_index_and_text.pos").alias("chunk_index"),
          F.col("chunk_index_and_text.col").alias("content")
      )
      .withColumn(
          "id",
          F.sha2(F.concat_ws("||", F.col("doc_id"), F.col("page_num").cast("string"),
                             F.lit("text"), F.col("chunk_index").cast("string")), 256)
      )
)

(gold_pdf_text_chunks.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_pdf_text_chunks"))


########################################Gold image items (rendered pages + embedded)######################################

gold_pdf_image_items = (
    spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_images")
      .select(
          F.sha2(F.concat_ws("||", F.col("doc_id"), F.col("page_num").cast("string"),
                             F.lit("image"), F.col("image_id")), 256).alias("id"),
          "doc_id",
          "page_num",
          "image_id",
          "image_kind",
          "image_name",
          "image_mime",
          "image_url",
          "pdf_url"
      )
)

(gold_pdf_image_items.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_pdf_image_items"))




###############################Optional unified Gold table (requested)###################################################


gold_text_unified = (
    spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_text_chunks")
      .select(
          "id", "doc_id", "page_num",
          F.lit("text").alias("item_type"),
          F.col("content"),
          F.lit(None).cast("string").alias("image_url"),
          F.col("pdf_url")
      )
)

gold_img_unified = (
    spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_image_items")
      .select(
          "id", "doc_id", "page_num",
          F.lit("image").alias("item_type"),
          F.lit(None).cast("string").alias("content"),
          F.col("image_url"),
          F.col("pdf_url")
      )
)

gold_pdf_items_unified = gold_text_unified.unionByName(gold_img_unified)

(gold_pdf_items_unified.write.mode("overwrite")
 .option("mergeSchema","true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_pdf_items_unified"))

display(spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_items_unified").limit(20))
