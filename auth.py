import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("ACCESS_KEY_SECRET")

TOKEN_FILE = "nice_token.json"


def load_cached_token():
    """Load token from cache if still valid"""
    if not os.path.exists(TOKEN_FILE):
        return None

    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)

        if time.time() < data.get("expires_at", 0):
            print("Using cached NICE token ✅")
            return data.get("access_token")
    except (json.JSONDecodeError, KeyError):
        return None

    return None


def save_token(token, expires_in):
    """Save token to cache with expiration"""
    payload = {
        "access_token": token,
        "expires_at": int(time.time()) + expires_in
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(payload, f)


def invalidate_token():
    """Delete cached token (call this on 401 errors)"""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print("Cached token invalidated")


def get_access_token(force_refresh=False):
    """Get access token (from cache or fresh request)"""
    
    # Try cached token first (unless forced refresh)
    if not force_refresh:
        cached = load_cached_token()
        if cached:
            return cached

    print("Requesting new NICE access token...")

    url = f"{BASE_URL}/authentication/v1/token/access-key"
    headers = {"Content-Type": "application/json"}

    payload = {
        "accessKeyId": ACCESS_KEY_ID,
        "accessKeySecret": ACCESS_KEY_SECRET
    }

    response = requests.post(url, json=payload, headers=headers, verify=False)

    if response.status_code != 200:
        print(f"❌ Failed to fetch token (Status {response.status_code})")
        print("Response:", response.text)
        return None

    token_data = response.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", 43200)

    save_token(access_token, expires_in)
    print("✅ New token saved to file")
    
    return access_token