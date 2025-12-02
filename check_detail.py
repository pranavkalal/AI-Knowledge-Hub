import requests
from bs4 import BeautifulSoup

url = "https://www.insidecotton.com/health-and-safety-data-australian-cotton-farms"
resp = requests.get(url)
soup = BeautifulSoup(resp.text, "html.parser")
pdfs = []
for a in soup.find_all("a", href=True):
    if a["href"].endswith(".pdf"):
        pdfs.append(a["href"])

print(f"Found {len(pdfs)} PDFs on {url}:")
for p in pdfs:
    print(p)
