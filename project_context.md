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
- **LLM**: OpenAI `gpt-4o`
- **Embeddings**: OpenAI `text-embedding-3-large` (3072-dim)
- **PDF Parsing**: Azure Document Intelligence (Layout model with bbox extraction)
- **Vector Store**: PostgreSQL + `pgvector` (hybrid search)
- **Reranking**: OpenAI embedding-based cross-encoder

### Frontend
- **Framework**: Next.js (React 19)
- **Styling**: Tailwind CSS, shadcn/ui
- **State Management**: Zustand
- **PDF Rendering**: `react-pdf` with deep linking highlights

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Database**: PostgreSQL 16 with pgvector extension

## Key Features
1.  **Hybrid Search**: Combines dense vector similarity with keyword search using PostgreSQL `tsvector`.
2.  **Deep Linking**: Stores bounding box coordinates for text chunks, allowing the frontend to highlight exact passages in the PDF.
3.  **Semantic Chunking**: Context-aware chunking that respects document structure (sections, paragraphs) with bbox mapping.
4.  **Citation Support**: Answers include citations that link directly to the source document and page.
5.  **Persona-Based Responses**: Adapts answer style for growers, researchers, or extension officers.
6.  **Reranking**: Cross-encoder reranking for improved retrieval precision.

## Data Flow
1.  **Ingestion**: PDFs in `data/raw` are parsed using Azure Document Intelligence, extracting Markdown text and bounding boxes.
2.  **Processing**: Text is semantically chunked with bbox coordinates preserved, then embedded using OpenAI.
3.  **Storage**: Metadata, text chunks, embeddings, and bboxes are stored in PostgreSQL with pgvector.
4.  **Retrieval**: User queries are embedded and matched via hybrid search. Top matches are reranked.
5.  **Generation**: Retrieved context is sent to GPT-4o with persona-aware prompts to generate cited answers.
