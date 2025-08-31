import json, csv, statistics as st, pathlib

IN = pathlib.Path("data/staging/docs.jsonl")
OUT = pathlib.Path("reports/extraction_audit.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

rows=[]
with IN.open("r", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        text = r.get("text","") or ""
        chars = len(text)
        m = r.get("meta", {}) or {}
        pages = int(m.get("pages", 0))
        cpp = (chars // max(pages,1)) if pages else 0

        if pages == 0:
            # No page info: use chars-only thresholds
            if chars >= 5000:
                grade = "PASS"
            elif chars < 1000:
                grade = "FAIL"
            else:
                grade = "REVIEW"
        else:
            # With pages: use both
            if pages >= 3 and chars >= 5000 and cpp >= 300:
                grade = "PASS"
            elif chars < 1000 or cpp < 100:
                grade = "FAIL"
            else:
                grade = "REVIEW"

        rows.append({
            "id": r.get("id",""),
            "title": r.get("title",""),
            "year": r.get("year",""),
            "filename": r.get("filename",""),
            "pages": pages,
            "text_chars": chars,
            "chars_per_page": cpp,
            "grade": grade,
        })

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)

chars = [r["text_chars"] for r in rows]
print(f"Docs: {len(rows)} | PASS {sum(r['grade']=='PASS' for r in rows)} | "
      f"REVIEW {sum(r['grade']=='REVIEW' for r in rows)} | "
      f"FAIL {sum(r['grade']=='FAIL' for r in rows)} | "
      f"median chars {int(st.median(chars)) if chars else 0}")
print("Wrote", OUT)
