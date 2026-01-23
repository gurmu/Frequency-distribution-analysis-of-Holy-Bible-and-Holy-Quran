# ==========
# ADLS GEN2 CONFIG (Azure Gov)
# ==========

STORAGE_ACCT = "stitsmdevz33lh8"
SRC_CONTAINER = "itsm-kb"
DST_CONTAINER = "pdfitsm"

# IMPORTANT CHANGE after upgrade:
# Use DFS endpoint (not blob) + ABFSS paths (not WASBS)
DFS_ENDPOINT = "dfs.core.usgovcloudapi.net"

# BEST PRACTICE:
# STORAGE_KEY = dbutils.secrets.get(scope="YOUR_SCOPE", key="stitsmdevz33lh8-storage-key")

# TEMP ONLY:
STORAGE_KEY = "<PASTE_STORAGE_ACCOUNT_KEY>"

# Spark auth (key-based)
spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCT}.{DFS_ENDPOINT}", STORAGE_KEY)

# ABFSS roots
SRC_ROOT = f"abfss://{SRC_CONTAINER}@{STORAGE_ACCT}.{DFS_ENDPOINT}/"
DST_ROOT = f"abfss://{DST_CONTAINER}@{STORAGE_ACCT}.{DFS_ENDPOINT}/"

print("SRC_ROOT:", SRC_ROOT)
print("DST_ROOT:", DST_ROOT)

dbutils.fs.mkdirs(DST_ROOT)