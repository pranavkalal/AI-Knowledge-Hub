# verify_migration.py
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

# Mock missing dependencies in sys.modules to avoid ImportErrors
sys.modules["azure.ai.formrecognizer"] = MagicMock()
sys.modules["azure.core.credentials"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()
sys.modules["sqlalchemy"].__spec__ = MagicMock() # Satisfy importlib.util.find_spec
sys.modules["sqlalchemy.orm"] = MagicMock()
sys.modules["pgvector"] = MagicMock()

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Reset env vars
        if "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT" in os.environ:
            del os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
        if "AZURE_DOCUMENT_INTELLIGENCE_KEY" in os.environ:
            del os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]
        if "POSTGRES_CONNECTION_STRING" in os.environ:
            del os.environ["POSTGRES_CONNECTION_STRING"]

    def test_azure_parser(self):
        print("\nTesting Azure Parser...")
        # We need to reload the module to pick up the mocked sys.modules if it was already loaded
        if "rag.ingest_lib.parser_azure" in sys.modules:
            del sys.modules["rag.ingest_lib.parser_azure"]
            
        # Mock the classes inside the module (which are now mocks from sys.modules)
        with patch("rag.ingest_lib.parser_azure.DocumentAnalysisClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            
            mock_poller = MagicMock()
            mock_result = MagicMock()
            mock_result.content = "This is a test PDF content."
            mock_result.pages = [MagicMock(), MagicMock()] # 2 pages
            mock_result.tables = []
            
            mock_poller.result.return_value = mock_result
            mock_client.begin_analyze_document.return_value = mock_poller
            
            # Set env vars
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = "https://test.cognitiveservices.azure.com/"
            os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "fake_key"
            
            from rag.ingest_lib.parser_azure import parse_pdf
            
            # Create a dummy PDF file
            with open("test.pdf", "wb") as f:
                f.write(b"%PDF-1.4 dummy content")
                
            try:
                parsed = parse_pdf("test.pdf")
                print(f"✅ Parsed text: {parsed.text}")
                print(f"✅ Page count: {parsed.meta['page_count']}")
                self.assertEqual(parsed.text, "This is a test PDF content.")
                self.assertEqual(parsed.meta["page_count"], 2)
            finally:
                if os.path.exists("test.pdf"):
                    os.remove("test.pdf")

    def test_postgres_adapter(self):
        print("\nTesting Postgres Adapter...")
        if "app.adapters.vector_postgres" in sys.modules:
            del sys.modules["app.adapters.vector_postgres"]

        # We need to mock create_engine and sessionmaker which are imported in the module
        # Since we mocked sqlalchemy in sys.modules, the module will import those mocks.
        # We just need to configure them.
        
        from app.adapters.vector_postgres import PostgresStoreAdapter
        
        # Configure the mocks that were imported
        # Note: PostgresStoreAdapter imports create_engine, text, sessionmaker from sqlalchemy
        # Since we mocked sqlalchemy, these are attributes of the mock.
        
        mock_sqlalchemy = sys.modules["sqlalchemy"]
        mock_engine = MagicMock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        mock_session_cls = sys.modules["sqlalchemy.orm"].sessionmaker
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        
        os.environ["POSTGRES_CONNECTION_STRING"] = "postgresql+psycopg2://user:pass@localhost:5432/db"
        
        # Test init (should create table)
        adapter = PostgresStoreAdapter()
        print("✅ Adapter initialized")
        
        # Test add_documents
        chunks = [{"id": "1", "text": "hello", "metadata": {"doc_id": "d1"}}]
        embeddings = [[0.1, 0.2, 0.3]]
        
        adapter.add_documents(chunks, embeddings)
        print("✅ add_documents called")
        
        # Verify insert was called
        self.assertTrue(mock_session.return_value.execute.called)
        self.assertTrue(mock_session.return_value.commit.called)

    def test_factory_postgres(self):
        print("\nTesting Factory with Postgres config...")
        # Mock PostgresStoreAdapter where it is defined, so when factory imports it, it gets the mock
        # But factory does `from app.adapters.vector_postgres import PostgresStoreAdapter`
        # So we need to patch it in `app.adapters.vector_postgres` OR mock the module.
        
        # Since we already mocked sys.modules["sqlalchemy"], importing vector_postgres is safe.
        # We can use patch on the module path.
        
        with patch("app.factory._load_cfg") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "vector_store": {"type": "postgres", "table_name": "test_chunks"},
                "embedder": {"provider": "openai", "model": "text-embedding-3-small"},
                "llm": {"adapter": "openai"}
            }
            
            # We patch the class in the module where it is defined
            with patch("app.adapters.vector_postgres.PostgresStoreAdapter") as MockAdapter:
                with patch("app.factory.load_embedder") as MockEmbedder:
                    os.environ["POSTGRES_CONNECTION_STRING"] = "dummy"
                    from app.factory import build_pipeline
                    pipeline = build_pipeline("dummy_config.yaml")
                    print("✅ Pipeline built with PostgresStoreAdapter")
                    self.assertTrue(MockAdapter.called)

if __name__ == "__main__":
    unittest.main()
