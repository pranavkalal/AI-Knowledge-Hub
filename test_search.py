import requests
import json

url = "http://localhost:8000/api/search"
params = {
    "q": "cotton yield 2024",
    "k": 3
}

try:
    resp = requests.get(url, params=params)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(json.dumps(resp.json(), indent=2))
    else:
        print(resp.text)
except Exception as e:
    print(f"Error: {e}")
