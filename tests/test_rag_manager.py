#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rag_manager.py — RAG 管理脚本逻辑验证。

分两部分：
  1) 纯逻辑（零依赖）：chunk_text 分块、collect_files 收集、load_config 结构。
  2) Chroma 集成（skipUnless chromadb 可用）：用 FakeEmbedding 离线跑通
     do_import 导入 + collection.query 检索，验证 RAG 主链路不依赖联网嵌入模型下载。
"""

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.rag_manager as rag_manager  # noqa: E402

CHROMADB_AVAILABLE = importlib.util.find_spec("chromadb") is not None


class RagPureTests(unittest.TestCase):
    """不依赖 chromadb 的纯逻辑测试。"""

    def test_chunk_text_basic(self):
        text = "A" * 1200  # 500 块，重叠 50 -> 步长 450
        chunks = rag_manager.chunk_text(text, size=500, overlap=50)
        self.assertTrue(len(chunks) >= 2)
        # 每块长度不超过 size
        for c in chunks:
            self.assertLessEqual(len(c), 500)
        # 末尾块非空
        self.assertTrue(chunks[-1])

    def test_chunk_text_overlap_recovery(self):
        text = "0123456789" * 100  # 1000 字符
        chunks = rag_manager.chunk_text(text, size=300, overlap=50)
        # 重建应大致覆盖原文（重叠区会有重复，但首尾要对得上）
        self.assertEqual(chunks[0][:10], text[:10])
        self.assertTrue(chunks[-1].endswith(text[-10:]))

    def test_chunk_text_empty(self):
        self.assertEqual(rag_manager.chunk_text("", 500, 50), [])
        self.assertEqual(rag_manager.chunk_text("   \n  ", 500, 50), [])

    def test_chunk_text_invalid_params(self):
        with self.assertRaises(ValueError):
            rag_manager.chunk_text("hello", size=50, overlap=50)
        with self.assertRaises(ValueError):
            rag_manager.chunk_text("hello", size=50, overlap=100)

    def test_load_config_structure(self):
        cfg = rag_manager.load_config()
        self.assertIn("chroma", cfg)
        self.assertIn("collection", cfg["chroma"])
        self.assertIn("supported_ext", cfg)
        self.assertIn(".md", cfg["supported_ext"])

    def test_collect_files_filters_by_ext(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "a.md").write_text("# hi", encoding="utf-8")
            (base / "b.txt").write_text("hi", encoding="utf-8")
            (base / "c.pdf").write_text("%PDF-1.4", encoding="utf-8")
            (base / "d.py").write_text("x=1", encoding="utf-8")  # 不应被收集
            sub = base / "sub"
            sub.mkdir()
            (sub / "e.md").write_text("nested", encoding="utf-8")
            # 非递归
            files = rag_manager.collect_files(base, recursive=False, cfg=rag_manager.load_config())
            names = sorted(p.name for p in files)
            self.assertEqual(names, ["a.md", "b.txt", "c.pdf"])
            # 递归
            files_r = rag_manager.collect_files(base, recursive=True, cfg=rag_manager.load_config())
            names_r = sorted(p.name for p in files_r)
            self.assertIn("e.md", names_r)


@unittest.skipUnless(CHROMADB_AVAILABLE, "chromadb 未安装，跳过 Chroma 集成测试")
class RagIntegrationTests(unittest.TestCase):
    """用 FakeEmbedding 离线验证 RAG 主链路（不触发联网嵌入模型下载）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rag_test_")
        # FakeEmbedding：固定维度、确定性向量，完全离线
        class FakeEmbedding:
            dim = 16
            is_legacy = False  # 抑制 chroma 关于 legacy embedding function 的 DeprecationWarning

            def name(self):
                return "fake-offline-test"

            def __call__(self, input):
                # chroma 1.x 接口：__call__(self, input: list[str]) -> list[list[float]]
                import hashlib
                out = []
                for t in input:
                    h = hashlib.sha256(t.encode("utf-8")).digest()
                    vec = [((h[i % len(h)] / 255.0) - 0.5) for i in range(self.dim)]
                    out.append(vec)
                return out

            def embed_documents(self, input):
                return self(input)

            def embed_query(self, input):
                if isinstance(input, list):
                    return self(input)
                return self([input])[0]

        self.fake = FakeEmbedding()
        # 把 get_embedding_fn 替换为返回 fake，避免 chroma-default 联网下载
        self._orig = rag_manager.get_embedding_fn
        rag_manager.get_embedding_fn = lambda cfg: self.fake
        # 指向临时持久化目录（绝对路径，避开真实 data/chroma）
        self.cfg = {
            "chroma": {"persist_dir": self.tmp, "collection": "test_offline_kb"},
            "embedding": {"provider": "chroma-default"},
            "chunk": {"size": 200, "overlap": 20},
            "supported_ext": [".md", ".txt", ".pdf"],
            "knowledge_dirs": [],
        }
        self.source_name = "tests/sample_doc.md"

    def tearDown(self):
        rag_manager.get_embedding_fn = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_doc(self):
        doc = Path(self.tmp) / "sample.md"
        doc.write_text(
            "# 三菱 FX5U Modbus 地址映射\n"
            "保持寄存器 40001 对应 D0，注意 1 基与 0 基偏移。\n"
            "线圈地址 00001 对应 M0。\n",
            encoding="utf-8",
        )
        return doc

    def test_import_and_query(self):
        doc = self._write_doc()
        added, skipped, failed = rag_manager.do_import([doc], self.cfg)
        self.assertEqual(failed, 0, "导入不应有失败")
        self.assertTrue(added > 0, "应至少导入一个块")

        # 通过同一 FakeEmbedding 检索，应返回刚导入的内容
        client = rag_manager.get_client(self.cfg)
        collection = client.get_collection(
            name=self.cfg["chroma"]["collection"], embedding_function=self.fake
        )
        self.assertTrue(collection.count() >= added)
        res = collection.query(query_texts=["FX5U 保持寄存器 D0 偏移"], n_results=1)
        self.assertTrue(len(res["documents"][0]) == 1)
        self.assertIn("FX5U", res["documents"][0][0])

    def test_idempotent_import(self):
        doc = self._write_doc()
        a1, _, _ = rag_manager.do_import([doc], self.cfg)
        a2, _, _ = rag_manager.do_import([doc], self.cfg)  # 相同内容二次导入
        client = rag_manager.get_client(self.cfg)
        count = client.get_collection(name=self.cfg["chroma"]["collection"]).count()
        # 幂等：相同内容 upsert 不产生新块
        self.assertEqual(count, a1, f"二次导入后块数应不变，期望 {a1}，实得 {count}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
