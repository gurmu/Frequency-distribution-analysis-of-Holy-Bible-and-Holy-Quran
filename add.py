B) Distributed uploader (NO collect, runs on executors)

Assumes you already set:

ACCOUNT = "stitsmdevz33lh8"

IMG_CONTAINER = "itsmimages"

BLOB_ENDPOINT = "blob.core.usgovcloudapi.net"

STORAGE_KEY = <Key1 from secrets>.strip()

from pyspark.sql import functions as F
import pandas as pd

# Make sure these exist in your notebook context:
# ACCOUNT, IMG_CONTAINER, BLOB_ENDPOINT, STORAGE_KEY

# Broadcast the key so executors can use it
bc_key = spark.sparkContext.broadcast(STORAGE_KEY)

# Choose upload layout (stable, deterministic)
# itsmimages/pdf_extracted_images/{doc_id}/{image_kind}/{image_name}
BASE_PREFIX = "pdf_extracted_images"

def upload_partition(iterator):
    """
    iterator yields pandas DataFrames (batches). We upload all rows in each batch.
    Return a pandas DataFrame with per-image status + url.
    """
    from azure.storage.blob import BlobServiceClient
    import traceback

    key = bc_key.value
    account = ACCOUNT
    blob_endpoint = BLOB_ENDPOINT
    container = IMG_CONTAINER
    base_prefix = BASE_PREFIX

    # Create the client once per partition
    bsc = BlobServiceClient(
        account_url=f"https://{account}.{blob_endpoint}",
        credential=key
    )
    cc = bsc.get_container_client(container)

    out_rows = []

    for pdf in iterator:
        for _, r in pdf.iterrows():
            doc_id     = r["doc_id"]
            page_num   = int(r["page_num"]) if r["page_num"] is not None else None
            image_id   = r["image_id"]
            image_kind = r["image_kind"]
            image_name = r["image_name"]
            image_mime = r["image_mime"]
            width      = int(r["width"]) if r["width"] is not None else 0
            height     = int(r["height"]) if r["height"] is not None else 0

            # pandas may store binary as bytes or memoryview
            img_bytes = r["image_bytes"]
            if img_bytes is None:
                out_rows.append({
                    "doc_id": doc_id, "page_num": page_num, "image_id": image_id,
                    "image_kind": image_kind, "image_name": image_name, "image_mime": image_mime,
                    "width": width, "height": height,
                    "image_url": None, "upload_ok": False,
                    "error": "image_bytes is null"
                })
                continue

            try:
                if isinstance(img_bytes, memoryview):
                    img_bytes = img_bytes.tobytes()
                elif not isinstance(img_bytes, (bytes, bytearray)):
                    img_bytes = bytes(img_bytes)

                blob_path = f"{base_prefix}/{doc_id}/{image_kind}/{image_name}"
                bc_client = cc.get_blob_client(blob_path)

                # Overwrite makes this idempotent (safe re-runs)
                bc_client.upload_blob(img_bytes, overwrite=True)

                url = f"https://{account}.{blob_endpoint}/{container}/{blob_path}"

                out_rows.append({
                    "doc_id": doc_id, "page_num": page_num, "image_id": image_id,
                    "image_kind": image_kind, "image_name": image_name, "image_mime": image_mime,
                    "width": width, "height": height,
                    "image_url": url, "upload_ok": True,
                    "error": None
                })

            except Exception as e:
                out_rows.append({
                    "doc_id": doc_id, "page_num": page_num, "image_id": image_id,
                    "image_kind": image_kind, "image_name": image_name, "image_mime": image_mime,
                    "width": width, "height": height,
                    "image_url": None, "upload_ok": False,
                    "error": f"{type(e).__name__}: {str(e)}"
                })

        yield pd.DataFrame(out_rows)
        out_rows = []  # flush batch output