# Databricks notebook - Option 1 (PDF multimodal)

from pyspark.sql import functions as F, types as T
import re, hashlib

# ---------- UC / Hive targets ----------
CATALOG = "hive_metastore"
SCHEMA  = "itsm"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# ---------- Azure Gov Storage ----------
ACCOUNT       = "stitsmdevz33lh8"                 # from your portal screenshot
DFS_ENDPOINT  = "dfs.core.usgovcloudapi.net"
BLOB_ENDPOINT = "blob.core.usgovcloudapi.net"

PDF_CONTAINER = "pdfitsm"                         # your container with ~120 PDFs
IMG_CONTAINER = "itsmimages"                      # your empty container for images

# ABFSS roots (NOTE: end with '/')
PDF_ROOT = f"abfss://{PDF_CONTAINER}@{ACCOUNT}.{DFS_ENDPOINT}/"
IMG_ROOT = f"abfss://{IMG_CONTAINER}@{ACCOUNT}.{DFS_ENDPOINT}/"

print("PDF_ROOT:", PDF_ROOT)
print("IMG_ROOT:", IMG_ROOT)

# ---------- Helpers ----------
def abfss_to_https(abfss_path: str) -> str:
    """
    Convert: abfss://container@account.dfs.core.usgovcloudapi.net/folder/file.pdf
    To:      https://account.blob.core.usgovcloudapi.net/container/folder/file.pdf
    """
    if not abfss_path:
        return None
    m = re.match(r"^abfss://([^@]+)@([^.]+)\.dfs\.core\.usgovcloudapi\.net/(.+)$", abfss_path)
    if not m:
        return None
    container, account, key = m.groups()
    return f"https://{account}.{BLOB_ENDPOINT}/{container}/{key}"

abfss_to_https_udf = F.udf(abfss_to_https, T.StringType())

def sha256_str(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8", errors="ignore")).hexdigest()

sha256_udf = F.udf(sha256_str, T.StringType())
