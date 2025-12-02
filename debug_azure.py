import os
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

print(f"Endpoint: {endpoint}")
if endpoint:
    print(f"Endpoint (masked): {endpoint[:15]}...")

try:
    client = DocumentIntelligenceClient(
        endpoint=endpoint, 
        credential=AzureKeyCredential(key),
        api_version="2023-10-31-preview"
    )
    poller = client.begin_analyze_document(
        "prebuilt-layout", 
        {
            "url_source": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf"
        }
    )
    result = poller.result()
    print("Success!")
    print(result.content[:100])

except Exception as e:
    print(f"Error: {e}")
