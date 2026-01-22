import os
import requests
from dotenv import load_dotenv

load_dotenv()

endpoint = os.environ["AZSEARCH_ENDPOINT"].rstrip("/")
admin_key = os.environ["AZSEARCH_ADMIN_KEY"]
api_version = os.getenv("AZSEARCH_API_VERSION", "2023-11-01")

headers = {"api-key": admin_key, "Content-Type": "application/json"}

r = requests.get(f"{endpoint}/indexes?api-version={api_version}", headers=headers, timeout=30)

print("STATUS:", r.status_code)
print(r.text[:1000])