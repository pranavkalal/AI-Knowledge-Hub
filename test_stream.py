import requests
import json

url = "http://localhost:8000/api/ask"
payload = {
    "question": "what is the cotton yield in 2024?",
    "k": 3,
    "max_output_tokens": 100
}

print(f"Testing streaming from {url}...")
try:
    with requests.post(url, json=payload, params={"stream": "true"}, stream=True) as r:
        print(f"Status: {r.status_code}")
        if r.status_code != 200:
            print(r.text)
        else:
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    print(f"Received: {decoded}")
                    if decoded.startswith("data: "):
                        data_str = decoded[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "error":
                                print(f"ERROR IN STREAM: {data}")
                        except:
                            pass
except Exception as e:
    print(f"Request failed: {e}")
