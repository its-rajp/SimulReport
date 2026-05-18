import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    response = requests.get(url)
    models = response.json().get('models', [])
    for m in models:
        print(m['name'])
except Exception as e:
    print("Error:", e)
