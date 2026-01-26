CHUNK_SIZE = 1200
OVERLAP    = 150

def chunk_text(text: str, size=CHUNK_SIZE, overlap=OVERLAP):
    if not text:
        return []
    words = text.split()
    out = []
    i = 0
    while i < len(words):
        out.append(" ".join(words[i:i+size]))
        i += max(1, (size - overlap))
    return out

chunk_udf = F.udf(lambda s: chunk_text(s), T.ArrayType(T.StringType()))

silver_pages_df = spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_pages")

gold_text = (
    silver_pages_df
      .withColumn("chunks", chunk_udf(F.col("page_text_clean")))
      .withColumn("chunk_index", F.posexplode(F.col("chunks")).getField("pos"))
      .withColumn("content", F.posexplode(F.col("chunks")).getField("col"))
      .drop("chunks")
      .withColumn("item_type", F.lit("text"))
      .withColumn(
          "id",
          F.concat_ws("-", F.col("doc_id"), F.lit("t"), F.format_string("%04d", F.col("page_num")), F.col("chunk_index").cast("string"))
      )
      .select(
          "id", "doc_id", "page_num", "item_type",
          F.col("content"),
          F.lit(None).cast("string").alias("image_url"),
          F.col("pdf_url")
      )
)

(gold_text.write.mode("overwrite")
 .option("mergeSchema", "true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_pdf_text_chunks"))
