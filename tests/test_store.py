"""store.build_db 단위 테스트. API 키와 실제 Chroma 없이 돈다."""

import sys
import types
import unittest
from unittest import mock

try:
    import langchain_chroma  # noqa: F401
except Exception:  # sqlite3가 낮아 chromadb를 import하지 못하는 환경
    stub = types.ModuleType("langchain_chroma")
    stub.Chroma = type("Chroma", (), {})
    sys.modules["langchain_chroma"] = stub

from langchain_core.documents import Document

from src import config
from src.db import store

DOCS = [Document(page_content="제1조(목적)", metadata={"page": 1})] * 3


class BuildDbTest(unittest.TestCase):
    def setUp(self):
        patches = {
            "load": mock.patch.object(store, "load_and_split", return_value=DOCS),
            "embed": mock.patch.object(store, "OpenAIEmbeddings"),
            "chroma": mock.patch.object(store, "Chroma"),
        }
        self.m = {name: p.start() for name, p in patches.items()}
        for p in patches.values():
            self.addCleanup(p.stop)

    def test_returns_chroma_built_from_all_chunks(self):
        db = store.build_db("x.pdf")

        self.m["load"].assert_called_once_with("x.pdf")
        self.assertIs(db, self.m["chroma"].from_documents.return_value)
        args, _ = self.m["chroma"].from_documents.call_args
        self.assertEqual(args[0], DOCS)
        self.assertIs(args[1], self.m["embed"].return_value)

    def test_embeddings_use_configured_model_without_key_argument(self):
        store.build_db("x.pdf")

        self.m["embed"].assert_called_once_with(model=config.EMBEDDING_MODEL)

    def test_each_call_uses_a_new_collection_name(self):
        store.build_db("x.pdf")
        store.build_db("x.pdf")

        names = [c.kwargs["collection_name"] for c in self.m["chroma"].from_documents.call_args_list]
        self.assertEqual(len(set(names)), 2)

    def test_loader_value_error_propagates_without_embedding(self):
        self.m["load"].side_effect = ValueError("제3조 p.2: 조 번호 역행")

        with self.assertRaisesRegex(ValueError, "제3조 p.2"):
            store.build_db("x.pdf")
        self.m["embed"].assert_not_called()
        self.m["chroma"].from_documents.assert_not_called()

    def test_empty_chunks_raise_without_embedding(self):
        self.m["load"].return_value = []

        with self.assertRaises(ValueError):
            store.build_db("x.pdf")
        self.m["embed"].assert_not_called()
        self.m["chroma"].from_documents.assert_not_called()

    def test_embedding_error_is_not_wrapped(self):
        self.m["chroma"].from_documents.side_effect = RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            store.build_db("x.pdf")


if __name__ == "__main__":
    unittest.main()
