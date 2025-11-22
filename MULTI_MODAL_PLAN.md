# Multi-Modal RAG & Deep Linking Upgrade Plan

This plan outlines how to upgrade the system to support **Multi-Modal RAG** (extracting and reasoning over images/tables) and **Deep Linking** (citations linking to exact PDF coordinates).

## 1. The Problem
- **Current State**: Uses `pypdf` to extract raw text. Ignores images, charts, and tables. No coordinate data is preserved.
- **Desired State**: Extract text + images + bounding boxes. Citations link to specific highlights in the PDF viewer.

## 2. Recommended Open Source Stack

### OCR & Parsing: **Docling** (by IBM)
- **Why**: It is state-of-the-art, open-source (MIT), and handles complex layouts, tables, and images excellently. It outputs Markdown with embedded image references and bounding boxes.
- **Alternative**: `Surya` (for pure OCR) or `Marker` (for Markdown conversion), but Docling is currently the most robust all-in-one solution.

### Deep Linking: **PDF.js + URL Fragments**
- **Mechanism**: Serve PDFs via a custom viewer (based on PDF.js) that accepts URL parameters like `#page=5&rect=100,200,300,400`.
- **Implementation**: The API will return `bbox` (bounding box) data with every citation. The UI will construct the link.

## 3. Implementation Steps

### Step 1: Upgrade Ingestion (`rag/ingest_lib`)
- [ ] **Replace `pypdf` with `docling`**.
- [ ] **Extract Images**: Save extracted images to `data/assets/` and reference them in the text chunks.
- [ ] **Preserve Coordinates**: Store `bbox` (x, y, w, h) and `page_number` for every text segment in `docs.jsonl`.

### Step 2: Multi-Modal Indexing
- [ ] **Embed Images**: Use a multi-modal model (like **CLIP** or **SigLIP**) to embed the extracted images.
- [ ] **Hybrid Retrieval**: Search both text (BM25/Dense) and images (CLIP) to find relevant charts/graphs.

### Step 3: Deep Linking UI
- [ ] **API Update**: Update `/api/ask` to return `page` and `bbox` in the `citations` list.
- [ ] **PDF Viewer**: Integrate a Streamlit component (or simple iframe) that loads the PDF and highlights the specific box.
    - Format: `/api/pdf/{doc_id}#page={page}&highlight={x},{y},{w},{h}`

## 4. Example Workflow
1.  **Ingest**: `report.pdf` -> Docling -> Markdown + Images + BBoxes.
2.  **Ask**: "What is the yield trend in Figure 3?"
3.  **Retrieve**: System finds the text description of Figure 3 AND the image itself.
4.  **Answer**: LLM sees the image and text, answers "Yields increased by 15%...".
5.  **Citation**: Link `[S1]` points to `report.pdf` Page 12, highlighting the chart.

## 5. Dependencies to Add
- `docling`
- `torch` (already present)
- `pillow` (for image handling)
