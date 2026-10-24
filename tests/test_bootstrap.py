#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bootstrap.py — deploy/bootstrap.py 的纯函数与目录初始化验证（零依赖）。

不实际创建 venv / 安装依赖 / 安装 Ollama（这些有副作用，留作 --dry-run 与手动执行）。
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import deploy.bootstrap as bootstrap  # noqa: E402


class BootstrapPureTests(unittest.TestCase):

    def test_parse_python_version(self):
        self.assertEqual(bootstrap.parse_python_version("Python 3.13.14"), (3, 13))
        self.assertEqual(bootstrap.parse_python_version("Python 3.10"), (3, 10))
        self.assertEqual(bootstrap.parse_python_version("3.9.2"), (3, 9))
        self.assertIsNone(bootstrap.parse_python_version("not a version"))

    def test_parse_requirements(self):
        text = """
# 注释行
chromadb>=0.6.0,<2.0.0
pypdf>=4.0.0
some-pkg[extra1,extra2]==1.2.3   # 行内注释
-r other.txt
"""
        parsed = bootstrap.parse_requirements(text)
        names = [p["name"] for p in parsed]
        self.assertIn("chromadb", names)
        self.assertIn("pypdf", names)
        # 行内注释被剥离
        chroma = next(p for p in parsed if p["name"] == "chromadb")
        self.assertEqual(chroma["spec"], ">=0.6.0,<2.0.0")
        # 带 extras 与 ==
        sp = next(p for p in parsed if p["name"] == "some-pkg")
        self.assertIn("extra1", sp["spec"])
        self.assertIn("==1.2.3", sp["spec"])

    def test_ensure_dirs_creates_skeleton(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bootstrap.ensure_dirs(root, dry_run=False)
            for d in bootstrap.required_dirs():
                self.assertTrue((root / d).is_dir(), f"目录未创建: {d}")
            for g in bootstrap.required_gitkeeps():
                self.assertTrue((root / g).exists(), f"占位文件未创建: {g}")

    def test_detect_python_returns_usable(self):
        # 当前运行解释器若是 3.10+，应返回可用路径
        if sys.version_info[:2] >= (3, 10):
            self.assertTrue(bootstrap.detect_python())
        else:  # pragma: no cover
            self.assertIsNotNone(bootstrap.detect_python())

    def test_dry_run_does_not_create(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bootstrap.ensure_dirs(root, dry_run=True)
            # dry-run 不应创建任何内容
            self.assertEqual(list(root.iterdir()), [],
                             "dry-run 不应在磁盘上创建任何内容")


if __name__ == "__main__":
    unittest.main(verbosity=2)
