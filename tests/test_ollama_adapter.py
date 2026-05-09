import unittest
from unittest.mock import patch

from app.adapters.ollama_adapter import OllamaAdapter


class OllamaAdapterTests(unittest.TestCase):
    def test_missing_local_ollama_returns_empty_list(self):
        with patch("urllib.request.urlopen", side_effect=OSError("not running")):
            self.assertEqual(OllamaAdapter().fetch_models(), [])


if __name__ == "__main__":
    unittest.main()
