bronze_pdf_bin = (
  spark.read.format("binaryFile")
    .option("recursiveFileLookup", "true")
    .load(PDF_GLOB)
    .select(
      F.col("path"),
      F.regexp_extract("path", r"([^/]+)$", 1).alias("file_name"),
      F.col("modificationTime"),
      F.col("length"),
      F.col("content")
    )
    .withColumn("doc_id", F.sha2(F.col("path"), 256))
)

(bronze_pdf_bin.write.mode("overwrite")
 .option("mergeSchema", "true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_pdf_bin"))



###################################Helper extraction function (PyMuPDF)########################################

def extract_pdf_pages_and_images(pdf_bytes: bytes, doc_id: str, render_dpi: int = 150):
    """
    Returns:
      pages: list of {doc_id, page_num, page_text_raw, page_text_len}
      images: list of {doc_id, page_num, image_id, image_kind, image_name, image_mime, image_bytes, width, height}
        image_kind: 'embedded' or 'page_render'
    """
    pages = []
    images = []

    if not pdf_bytes:
        return pages, images

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for pno in range(len(doc)):
        page = doc[pno]

        # ---- TEXT (page-level) ----
        text = page.get_text("text") or ""
        pages.append({
            "doc_id": doc_id,
            "page_num": int(pno),
            "page_text_raw": text,
            "page_text_len": int(len(text)),
        })

        # ---- EMBEDDED IMAGES ----
        try:
            for img_idx, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base = doc.extract_image(xref)
                img_bytes = base.get("image", b"")
                ext = (base.get("ext") or "bin").lower()

                if ext in ["jpg", "jpeg"]:
                    mime = "image/jpeg"
                elif ext == "png":
                    mime = "image/png"
                else:
                    mime = "application/octet-stream"

                image_name = f"p{pno:04d}_embedded_{img_idx}.{ext}"
                image_id = sha256_str(f"{doc_id}||{pno}||embedded||{xref}||{image_name}||{len(img_bytes)}")

                images.append({
                    "doc_id": doc_id,
                    "page_num": int(pno),
                    "image_id": image_id,
                    "image_kind": "embedded",
                    "image_name": image_name,
                    "image_mime": mime,
                    "image_bytes": img_bytes,
                    "width": int(base.get("width") or 0),
                    "height": int(base.get("height") or 0),
                })
        except Exception:
            # embedded image extraction can fail on some PDFs; don't block whole job
            pass

        # ---- RENDERED PAGE IMAGE (PNG) ----
        pix = page.get_pixmap(dpi=render_dpi, alpha=False)
        png_bytes = pix.tobytes("png")

        image_name = f"page_{pno:04d}.png"
        image_id = sha256_str(f"{doc_id}||{pno}||page_render||{image_name}||{len(png_bytes)}")

        images.append({
            "doc_id": doc_id,
            "page_num": int(pno),
            "image_id": image_id,
            "image_kind": "page_render",
            "image_name": image_name,
            "image_mime": "image/png",
            "image_bytes": png_bytes,
            "width": int(pix.width),
            "height": int(pix.height),
        })

    doc.close()
    return pages, images


  #############################Write bronze_pdf_pages (page text)###########################################

  pdfs = spark.table(f"{CATALOG}.{SCHEMA}.bronze_pdf_bin").select("doc_id", "content")

pages_schema = T.StructType([
    T.StructField("doc_id", T.StringType()),
    T.StructField("page_num", T.IntegerType()),
    T.StructField("page_text_raw", T.StringType()),
    T.StructField("page_text_len", T.IntegerType()),
])

def pages_map(pdf_iter):
    for pdf_batch in pdf_iter:
        rows = []
        for _, r in pdf_batch.iterrows():
            pages, _ = extract_pdf_pages_and_images(r["content"], r["doc_id"])
            rows.extend(pages)
        yield pd.DataFrame(rows)

bronze_pages = pdfs.mapInPandas(pages_map, schema=pages_schema)

(bronze_pages.write.mode("overwrite")
 .option("mergeSchema", "true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_pdf_pages"))


##############################Write bronze_pdf_images (embedded + rendered bytes)###########################################

images_schema = T.StructType([
    T.StructField("doc_id", T.StringType()),
    T.StructField("page_num", T.IntegerType()),
    T.StructField("image_id", T.StringType()),
    T.StructField("image_kind", T.StringType()),
    T.StructField("image_name", T.StringType()),
    T.StructField("image_mime", T.StringType()),
    T.StructField("image_bytes", T.BinaryType()),
    T.StructField("width", T.IntegerType()),
    T.StructField("height", T.IntegerType()),
])

def images_map(pdf_iter):
    for pdf_batch in pdf_iter:
        rows = []
        for _, r in pdf_batch.iterrows():
            _, images = extract_pdf_pages_and_images(r["content"], r["doc_id"])
            rows.extend(images)
        yield pd.DataFrame(rows)

bronze_images = pdfs.mapInPandas(images_map, schema=images_schema)

(bronze_images.write.mode("overwrite")
 .option("mergeSchema", "true")
 .format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_pdf_images"))
