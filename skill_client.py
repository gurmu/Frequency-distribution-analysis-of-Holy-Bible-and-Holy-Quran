import os
import requests
from dotenv import load_dotenv
from auth import get_access_token, invalidate_token

load_dotenv()
API_URL = os.getenv("API_URL")


def get_skills():
    """Fetch skills with automatic token refresh on 401"""
    
    token = get_access_token()
    if not token:
        print("❌ No valid token available")
        return None

    url = f"{API_URL}/incontactAPI/services/v33.0/skills"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    print("Fetching skills from NICE inContact...")
    response = requests.get(url, headers=headers, verify=False)
    
    print(f"Status Code: {response.status_code}")

    # ✅ Auto-refresh on 401 (invalid token)
    if response.status_code == 401:
        print("⚠️ Token expired or invalid, refreshing...")
        invalidate_token()
        
        # Get fresh token and retry
        token = get_access_token(force_refresh=True)
        if not token:
            print("❌ Failed to refresh token")
            return None
        
        headers["Authorization"] = f"Bearer {token}"
        response = requests.get(url, headers=headers, verify=False)
        print(f"Retry Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ Failed to fetch skills")
        print("Response:", response.text)
        return None

    return response.json()