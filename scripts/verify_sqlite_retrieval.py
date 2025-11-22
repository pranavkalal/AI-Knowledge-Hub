import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure we use the right config
os.environ["COTTON_RUNTIME"] = "configs/runtime/openai.yaml"

from app.factory import build_pipeline

def verify():
    print("Building pipeline...")
    try:
        pipeline = build_pipeline()
    except Exception as e:
        print(f"Failed to build pipeline: {e}")
        return

    print("Pipeline built successfully.")
    
    query = "cotton yield"
    print(f"\nQuerying: '{query}'")
    
    try:
        result = pipeline.ask(query, k=3)
    except Exception as e:
        print(f"Query failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\nAnswer:")
    print(result['answer'])
    
    print("\nSources:")
    for src in result['sources']:
        print(f"- {src.get('title', 'No Title')} (Score: {src.get('score', 0):.4f})")
        print(f"  URL: {src.get('url')}")
        print(f"  Filename: {src.get('rel_path')}")
        print(f"  Snippet: {src.get('snippet', '')[:100]}...")
        
        if not src.get('url'):
            print("  ❌ URL missing! Deep linking failed.")
        else:
            print("  ✅ URL present.")
            
        if not src.get('rel_path'):
            print("  ❌ Filename missing! Metadata enrichment failed.")
        else:
            print("  ✅ Filename present.")

if __name__ == "__main__":
    verify()
