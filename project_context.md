# Project: CRDC AI Knowledge Hub

## Overview
The **CRDC AI Knowledge Hub** is an intelligent, RAG-based (Retrieval-Augmented Generation) system designed for the Australian Cotton Industry. It ingests, indexes, and makes searchable over 40 years of cotton research documents. The system allows users to ask natural language questions and receive evidence-based answers with direct citations and deep links to the source PDF documents.

## Architecture
The system is containerized using Docker and consists of the following core services:

- **API (`api`)**: A FastAPI backend that handles document ingestion, search queries, and RAG orchestration.
- **Frontend (`ui`)**: A Next.js application providing a chat interface and PDF viewer.
- **Database (`db`)**: PostgreSQL with `pgvector` for storing document metadata, text chunks, and vector embeddings.
- **Ingestion Pipeline**: A batch processing script that parses PDFs, chunks text, and generates embeddings.

## Tech Stack

### Backend & AI
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Orchestration**: LangChain (LCEL)
- **LLM**: OpenAI GPT-4o-mini
- **Embeddings**: OpenAI `text-embedding-3-small`
- **PDF Parsing**: IBM Docling (Multi-modal parsing)
- **Vector Store**: PostgreSQL (`pgvector`) / FAISS (Legacy/Hybrid)

### Frontend
- **Framework**: Next.js 16 (React 19)
- **Styling**: Tailwind CSS, shadcn/ui
- **State Management**: Zustand
- **PDF Rendering**: `react-pdf`

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Database**: PostgreSQL 16

## Key Features
1.  **Intelligent Retrieval**: Hybrid search combining dense vector similarity with keyword search (using PostgreSQL `tsvector` or BM25).
2.  **Deep Linking**: Stores bounding box coordinates for text chunks, allowing the frontend to highlight exact passages in the PDF.
3.  **Semantic Chunking**: Context-aware chunking that respects document structure (sections, paragraphs).
4.  **Citation Support**: Answers include citations that link directly to the source document and page.
5.  **Batched Ingestion**: Robust pipeline for processing large volumes of PDFs without memory issues.

## Data Flow
1.  **Ingestion**: PDFs are placed in `data/raw`. Scripts parse them using Docling, extracting text and layout info.
2.  **Processing**: Text is chunked semantically and embedded using OpenAI models.
3.  **Storage**: Metadata, text chunks, and embeddings are stored in PostgreSQL.
4.  **Retrieval**: User queries are embedded and matched against stored vectors. Top matches are reranked (optional).
5.  **Generation**: Retrieved context is sent to the LLM to generate an answer with citations.
