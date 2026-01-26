# Databricks notebook
# If you haven't installed PyMuPDF in this cluster:
# %pip install pymupdf
# dbutils.library.restartPython()

from pyspark.sql import functions as F, types as T
import re, hashlib, io
import pandas as pd
import fitz  # PyMuPDF

# ----------------------------
# REQUIRED: set these
# ----------------------------
CATALOG = "hive_metastore"
SCHEMA  = "itsm"

# Storage account and containers (Gov cloud uses *.dfs.core.usgovcloudapi.net for ABFSS)
ACCOUNT         = "stitsmdevz33lh8"     # from your screenshot
PDF_CONTAINER   = "pdfitsm"
IMG_CONTAINER   = "itsmimages"

# Optional: where to export JSONL for Azure AI Search to index Gold (recommended for Option 1)
GOLD_CONTAINER  = "itsmgold"            # create this container, or set to None to skip exports

# Paths
PDF_GLOB = f"abfss://{PDF_CONTAINER}@{ACCOUNT}.dfs.core.usgovcloudapi.net/**/*.pdf"

# Images will be written deterministically:
# abfss://itsmimages@<account>.dfs.../pdf_images/{doc_id}/page_{page_num:04d}.png
IMG_BASE_DIR = f"abfss://{IMG_CONTAINER}@{ACCOUNT}.dfs.core.usgovcloudapi.net/pdf_images"

# For later "click-back" URLs. In Gov, blob endpoint is typically *.blob.core.usgovcloudapi.net
# If your environment uses a different domain, change here.
def abfss_to_https(path: str) -> str:
    """
    Convert abfss://container@account.dfs.core.usgovcloudapi.net/dir/file
    -> https://account.blob.core.usgovcloudapi.net/container/dir/file
    """
    if not path:
        return None
    m = re.match(r"^abfss://([^@]+)@([^.]+)\.dfs\.core\.usgovcloudapi\.net/(.+)$", path)
    if not m:
        return None
    container, account, key = m.groups()
    return f"https://{account}.blob.core.usgovcloudapi.net/{container}/{key}"

def sha256_str(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8", errors="ignore")).hexdigest()



#####################################Two quick checks you should run#####################################


display(spark.table(f"{CATALOG}.{SCHEMA}.gold_pdf_items_unified").groupBy("item_type").count())
display(spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_images").limit(10))
display(spark.table(f"{CATALOG}.{SCHEMA}.silver_pdf_pages").limit(10))