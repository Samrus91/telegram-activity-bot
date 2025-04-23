import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL") + "/rest/v1/user_activity"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def insert_activity(data):
    response = requests.post(SUPABASE_URL, json=data, headers=HEADERS)
    return response.json()

def get_activity(user_id, post_id):
    params = {
        "user_id": f"eq.{user_id}",
        "post_id": f"eq.{post_id}"
    }
    response = requests.get(SUPABASE_URL, headers=HEADERS, params=params)
    return response.json()

def update_activity(user_id, post_id, update_data):
    url = f"{SUPABASE_URL}?user_id=eq.{user_id}&post_id=eq.{post_id}"
    response = requests.patch(url, headers=HEADERS, json=update_data)
    return response.json()