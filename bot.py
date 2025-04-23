app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

import os
from postgrest import SyncClient

SUPABASE_URL = os.environ.get("https://rwdkutiafmpuvigvnoiu.supabase.co") + "/rest/v1"
SUPABASE_KEY = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3ZGt1dGlhZm1wdXZpZ3Zub2l1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU0MDA5MDEsImV4cCI6MjA2MDk3NjkwMX0.oFH5lEyqMWXO9ebk7ODeabSBHeEW-AGWJ6a2VJqW-n8")
TELEGRAM_BOT_TOKEN = os.environ.get("7454880277:AAEXrtwlCJFLjXBnqXs7lPS8-0jgPbUKv-s")

supabase = SyncClient(SUPABASE_URL, headers={
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
})