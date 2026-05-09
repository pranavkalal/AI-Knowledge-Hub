from __future__ import annotations

import argparse
from pathlib import Path

from app.db import SessionLocal, init_db
from app.services.export import export_records_csv, export_records_json
from app.services.update_pipeline import import_manual_seed, records_for_export, reclassify_all, run_update_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="GraphRAG LLM dashboard admin commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("update", help="Run all configured source adapters")
    seed = subparsers.add_parser("import-seed", help="Import manual seed file")
    seed.add_argument("--path", default="data/manual_models.seed.json")
    subparsers.add_parser("reclassify", help="Reclassify all stored models")
    export = subparsers.add_parser("export", help="Export stored models")
    export.add_argument("--format", choices=["csv", "json"], default="csv")
    export.add_argument("--out", default="")

    args = parser.parse_args()
    init_db()
    with SessionLocal() as db:
        if args.command == "update":
            result = run_update_pipeline(db)
            print(result)
        elif args.command == "import-seed":
            result = import_manual_seed(db, args.path)
            print(result)
        elif args.command == "reclassify":
            print(f"Reclassified {reclassify_all(db)} models")
        elif args.command == "export":
            records = records_for_export(db)
            content = export_records_csv(records) if args.format == "csv" else export_records_json(records)
            if args.out:
                Path(args.out).write_text(content, encoding="utf-8")
                print(f"Wrote {args.out}")
            else:
                print(content)


if __name__ == "__main__":
    main()
