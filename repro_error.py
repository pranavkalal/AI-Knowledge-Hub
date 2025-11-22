import sys
import os
from app.factory import build_pipeline

try:
    print("Building pipeline...")
    pipe = build_pipeline()
    print("Pipeline built. Asking question...")
    res = pipe.ask(question="What is the revenue?", k=2)
    print("Result:", res)
except Exception:
    import traceback
    traceback.print_exc()
