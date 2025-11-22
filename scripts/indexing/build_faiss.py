"""
Legacy entry point kept for backwards compatibility.

Delegates to scripts.build.faiss.main().
"""

from scripts.build.faiss import main


if __name__ == "__main__":
    main()
