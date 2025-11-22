#!/usr/bin/env python3
"""
Safe repository cleanup script.
Completes the reorganization plan with conflict detection and verification.
"""
import os
import shutil
from pathlib import Path
from typing import List, Tuple

def main():
    repo_root = Path("/Users/viking/AI-Knowledge-Hub")
    os.chdir(repo_root)
    
    moves: List[Tuple[str, str]] = []
    deletes: List[str] = []
    
    print("🔍 Planning cleanup operations...\n")
    
    # ===== SCRIPTS REORGANIZATION =====
    scripts_moves = [
        # Ingestion
        ("scripts/ingest_openai.py", "scripts/ingestion/run_ingestion.py"),
        ("scripts/ingest_excel.py", "scripts/ingestion/import_excel.py"),
        ("scripts/merge_ingestion.py", "scripts/ingestion/merge_metadata.py"),
        
        # Indexing
        ("scripts/build_embeddings.py", "scripts/indexing/build_embeddings.py"),
        ("scripts/build_faiss.py", "scripts/indexing/build_faiss.py"),
        
        # Evaluation
        ("scripts/eval_retrieval.py", "scripts/evaluation/eval_retrieval.py"),
        ("scripts/regress_retrieval.py", "scripts/evaluation/regress_retrieval.py"),
        
        # Utils
        ("scripts/query_faiss.py", "scripts/utils/query_faiss.py"),
        ("scripts/verify_sqlite_retrieval.py", "scripts/utils/verify_pipeline.py"),
        ("scripts/retry_downloads.py", "scripts/utils/retry_downloads.py"),
        ("scripts/monitor_ingestion.sh", "scripts/utils/monitor_ingestion.sh"),
        
        # Tools
        ("scripts/test_docling_parser.py", "tools/test_docling.py"),
        ("scripts/test_semantic_chunking.py", "tools/test_chunking.py"),
    ]
    
    # Files to delete (redundant)
    scripts_deletes = [
        "scripts/ingest_docling.py",
        "scripts/ingest_docling_slow.py",
        "scripts/ingest_finish.py",
        "scripts/finalize_ingestion.py",
        "scripts/ingest_test_pdf.py",
    ]
    
    # ===== RAG RESTRUCTURE =====
    rag_moves = [
        ("rag/ingest_lib/parse_docling.py", "rag/ingest/parsers/docling_parser.py"),
        ("rag/segment/semantic_chunker.py", "rag/ingest/chunkers/semantic.py"),
        ("rag/segment/chunker.py", "rag/ingest/chunkers/base.py"),
        ("rag/segment/tiktoken_wrapper.py", "rag/ingest/chunkers/tiktoken_wrapper.py"),
    ]
    
    rag_dir_deletes = [
        "rag/ingest_lib",
        "rag/segment",
    ]
    
    # ===== CONFIG =====
    config_ops = [
        ("configs", "config"),  # Rename directory
    ]
    
    # ===== REDUNDANT DIRS =====
    dir_deletes = [
        "store",
        "ui",
    ]
    
    # Combine all operations
    moves.extend(scripts_moves)
    moves.extend(rag_moves)
    deletes.extend(scripts_deletes)
    
    # Create necessary directories
    print("📁 Creating directories...")
    dirs_to_create = [
        "scripts/ingestion",
        "scripts/indexing",
        "scripts/evaluation",
        "scripts/utils",
        "tools",
        "rag/ingest/parsers",
        "rag/ingest/chunkers",
        "config",
    ]
    
    for d in dirs_to_create:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {d}")
    
    # Execute moves
    print("\n📦 Moving files...")
    moved_count = 0
    skipped_count = 0
    
    for src, dst in moves:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            print(f"  ⏭️  Skip (not found): {src}")
            skipped_count += 1
            continue
        
        if dst_path.exists():
            print(f"  ⚠️  Skip (exists): {dst}")
            skipped_count += 1
            continue
        
        try:
            shutil.move(str(src_path), str(dst_path))
            print(f"  ✅ {src} → {dst}")
            moved_count += 1
        except Exception as e:
            print(f"  ❌ Failed: {src} → {dst}: {e}")
    
    # Delete redundant files
    print("\n🗑️  Deleting redundant files...")
    deleted_count = 0
    
    for f in deletes:
        fpath = Path(f)
        if fpath.exists():
            try:
                fpath.unlink()
                print(f"  ✅ Deleted: {f}")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ Failed to delete {f}: {e}")
        else:
            print(f"  ⏭️  Already gone: {f}")
    
    # Delete redundant directories
    print("\n🗑️  Deleting redundant directories...")
    for d in rag_dir_deletes + dir_deletes:
        dpath = Path(d)
        if dpath.exists():
            try:
                shutil.rmtree(dpath)
                print(f"  ✅ Deleted: {d}/")
            except Exception as e:
                print(f"  ❌ Failed: {d}: {e}")
    
    # Rename configs → config
    if Path("configs").exists() and not Path("config").exists():
        shutil.move("configs", "config")
        print("  ✅ Renamed: configs → config")
    
    # Summary
    print(f"\n✅ Cleanup complete!")
    print(f"   Moved: {moved_count} files")
    print(f"   Skipped: {skipped_count} files")
    print(f"   Deleted: {deleted_count} files")
    
    # Verify critical files exist
    print("\n🔍 Verifying critical files...")
    critical_files = [
        "scripts/ingestion/run_ingestion.py",
        "scripts/indexing/build_embeddings.py",
        "scripts/indexing/build_faiss.py",
        "rag/ingest/parsers/docling_parser.py",
        "rag/ingest/chunkers/semantic.py",
    ]
    
    all_good = True
    for f in critical_files:
        if Path(f).exists():
            print(f"  ✅ {f}")
        else:
            print(f"  ❌ MISSING: {f}")
            all_good = False
    
    if all_good:
        print("\n🎉 All critical files in place!")
    else:
        print("\n⚠️  Some files missing - check above")

if __name__ == "__main__":
    main()
