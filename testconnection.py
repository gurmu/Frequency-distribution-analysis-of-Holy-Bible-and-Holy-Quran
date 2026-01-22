import os
import json
import requests

SEARCH_ENDPOINT = os.getenv("AZSEARCH_ENDPOINT", "https://itsmmulti.search.azure.us").rstrip("/")
SEARCH_ADMIN_KEY = (os.getenv("AZSEARCH_ADMIN_KEY") or "").strip()

# Azure AI Search data-plane API version (NOT OpenAI)
SEARCH_API_VERSION = "2024-07-01"

# Use Storage connection string first (simplest + reliable).
# Later you can switch to managed identity/resourceId once everything works.
AZURE_STORAGE_CONNECTION_STRING = (os.getenv("AZURE_STORAGE_CONNECTION_STRING") or "").strip()

SOURCE_CONTAINER = "itsm-kb"
DATASOURCE_NAME = "itsm-docx-mm-ds"

def request(method: str, path: str, payload=None):
    if not SEARCH_ADMIN_KEY:
        raise RuntimeError("Missing AZSEARCH_ADMIN_KEY (must be an *admin* key, not query key).")

    url = f"{SEARCH_ENDPOINT}{path}"
    headers = {
        "api-key": SEARCH_ADMIN_KEY,
        "Content-Type": "application/json"
    }

    resp = requests.request(
        method=method,
        url=url,
        headers=headers,
        params={"api-version": SEARCH_API_VERSION},
        data=json.dumps(payload) if payload is not None else None,
        timeout=60,
    )

    if resp.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: {resp.status_code}\n{resp.text}")

    return resp.json() if resp.text else None

def main():
    # 1) Confirm auth works (equivalent to your PowerShell GET)
    print("Testing: GET indexes ...")
    indexes = request("GET", "/indexes")
    print("OK. Existing indexes:", [i["name"] for i in indexes.get("value", [])])

    # 2) Create/Update datasource
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise RuntimeError("Missing AZURE_STORAGE_CONNECTION_STRING. Add it temporarily to validate end-to-end. "
                           "We can switch to Managed Identity later.")

    datasource_payload = {
        "name": DATASOURCE_NAME,
        "type": "azureblob",
        "credentials": {"connectionString": AZURE_STORAGE_CONNECTION_STRING},
        "container": {"name": SOURCE_CONTAINER}
    }

    print("Creating datasource ...")
    out = request("PUT", f"/datasources/{DATASOURCE_NAME}", datasource_payload)
    print("Datasource created/updated:", out["name"])

if __name__ == "__main__":
    main()