# CRDC AI Knowledge Hub
*Unlocking 40+ years of Australian Cotton Research with AI.*

## 🚀 Overview

The **CRDC AI Knowledge Hub** is an intelligent search and question-answering system designed to make decades of agricultural research instantly accessible. By leveraging advanced **Retrieval-Augmented Generation (RAG)**, it transforms static PDF reports into a dynamic knowledge base, allowing researchers, agronomists, and stakeholders to ask questions and get evidence-based answers in seconds.

## ✨ Key Features

- **🤖 Intelligent Q&A**: Ask natural language questions like *"What are the best irrigation practices for cotton?"* and get comprehensive answers.
- **📄 Evidence-Based**: Every answer is backed by citations from official CRDC research papers.
- **🔍 Deep Linking**: Click a citation to jump directly to the exact paragraph in the original PDF source.
- **🧠 Advanced Understanding**: Uses state-of-the-art AI to understand context, tables, and technical terminology.
- **⚡ Hybrid Search**: Combines semantic understanding with keyword precision for accurate results.

## 🛠️ Technology Stack

Built with modern, scalable technologies:

- **AI & LLM**: OpenAI GPT-4o, Text-Embedding-3
- **RAG Orchestration**: LangGraph (Corrective RAG pattern)
- **Backend**: Python, FastAPI, LangChain
- **Frontend**: Next.js, React, Tailwind CSS
- **Database**: PostgreSQL (Vector Store & Metadata)
- **PDF Processing**: Azure Document Intelligence

## 📸 How It Works

1.  **Ingestion**: Research PDFs are processed to extract text, tables, and layout using Azure Document Intelligence.
2.  **Indexing**: Content is semantically analyzed, chunked, and stored in PostgreSQL with vector embeddings.
3.  **Retrieval**: User questions are matched with the most relevant research using hybrid search (Vector + Keyword).
4.  **Generation**: AI synthesizes an answer using *only* the retrieved facts, ensuring accuracy.

---

## 👨‍💻 Developer Guide

### Quick Start

**1. Clone & Install**
```bash
git clone https://github.com/your-org/AI-Knowledge-Hub.git
cd AI-Knowledge-Hub

# Install dependencies (Backend & Frontend)
make install
```

**2. Configure Environment**
```bash
cp .env.example .env
```
*Edit `.env` to add your `OPENAI_API_KEY` and `POSTGRES_CONNECTION_STRING`.*

**3. Run the App**
```bash
make dev
```
*This launches both the API (http://localhost:8000) and Frontend (http://localhost:3000).*

### Common Commands

| Command | Description |
| :--- | :--- |
| `make dev` | Run full stack (API + UI) |
| `make ingest` | Run PDF ingestion pipeline |
| `make test` | Run backend tests |
| `make fmt` | Format code |

### Repository Structure

- **`app/`**: FastAPI backend application
- **`frontend/`**: Next.js user interface
- **`rag/`**: Core RAG logic (Ingestion, Retrieval, Chains)
- **`scripts/`**: Utility scripts for data processing
- **`data/`**: Storage for raw PDFs and logs

## 📄 License

MIT License - see [LICENSE](LICENSE)
