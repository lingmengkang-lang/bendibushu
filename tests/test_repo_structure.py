#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_repo_structure.py — 仓库结构 / 配置 / 文档完整性（零依赖，纯 stdlib）

不依赖 chromadb / pytest，可在任意装有 Python 3.10+ 的机器上跑。
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import deploy.bootstrap as bootstrap  # noqa: E402

REQUIRED_FILES = [
    "README.md",
    "requirements.txt",
    "config/ollama-models.txt",
    "config/rag.config.json",
    "scripts/rag_manager.py",
    "scripts/start.ps1",
    "scripts/stop.ps1",
    "scripts/selfcheck.ps1",
    "scripts/setup_ollama.ps1",
    "deploy/install.ps1",
    "deploy/bootstrap.py",
    "deploy/setup.sh",
    "docs/plc/SAFETY.md",
    "docs/plc/brands.md",
    "docs/plc/hmi_scada_host.md",
    "docs/plc/how_to_extend.md",
    "docs/plc/brand_onboarding_template.md",
    "docs/scada/README.md",
    "docs/scada/kingview.md",
    "docs/scada/mcgs.md",
    "docs/scada/wincc.md",
    "docs/scada/forcecontrol.md",
    "docs/scada/weinview.md",
]

TOP5_DOCS = [
    "docs/scada/README.md",
    "docs/scada/kingview.md",
    "docs/scada/mcgs.md",
    "docs/scada/wincc.md",
    "docs/scada/forcecontrol.md",
    "docs/scada/weinview.md",
]

REQUIRED_DIRS = [
    "docs/plc",
    "docs/scada",
    "docs/host",
    "docs/devices",
    "data/knowledge_base/docs",
    "config",
    "scripts",
    "deploy",
    "tests",
]


class RepoStructureTests(unittest.TestCase):

    def test_required_files_exist(self):
        missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
        self.assertEqual(missing, [], f"缺失文件: {missing}")

    def test_required_dirs_exist(self):
        missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
        self.assertEqual(missing, [], f"缺失目录: {missing}")

    def test_scada_top5_present(self):
        missing = [f for f in TOP5_DOCS if not (ROOT / f).is_file()]
        self.assertEqual(missing, [], f"组态 TOP5 文档缺失: {missing}")

    def test_rag_config_json_valid(self):
        cfg_path = ROOT / "config/rag.config.json"
        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        self.assertIn("chroma", cfg)
        self.assertIn("collection", cfg["chroma"])
        self.assertIn("knowledge_dirs", cfg)
        # knowledge_dirs 列出的目录应都存在（不存在会导致 add-all/scan 静默跳过）
        for d in cfg["knowledge_dirs"]:
            self.assertTrue((ROOT / d).is_dir(), f"knowledge_dirs 指向不存在的目录: {d}")

    def test_requirements_parse(self):
        text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        parsed = bootstrap.parse_requirements(text)
        self.assertTrue(len(parsed) > 0, "requirements.txt 解析为空")
        # 每个条目都应能提取到包名
        for item in parsed:
            self.assertTrue(item["name"], f"无法提取包名: {item['raw']}")

    def test_ollama_models_txt_nonempty(self):
        text = (ROOT / "config/ollama-models.txt").read_text(encoding="utf-8")
        active = []
        for line in text.splitlines():
            t = line.strip()
            if not t or t.startswith("#"):
                continue
            active.append(t.split("#")[0].strip())
        self.assertTrue(len(active) > 0, "ollama-models.txt 没有任何未注释的模型")

    def test_ps1_scripts_have_bom(self):
        ps1_files = sorted((ROOT / "scripts").glob("*.ps1")) + [ROOT / "deploy/install.ps1"]
        for ps in ps1_files:
            if not ps.is_file():
                continue
            raw = ps.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"),
                            f"PS1 缺少 UTF-8 BOM（PowerShell 5.1 中文会乱码）: {ps.name}")

    def test_markdown_links_resolve(self):
        """粗粒度检查：docs 与 README 中的相对链接目标应存在（跳过代码块内示例链接）。"""
        import re
        link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        fence_re = re.compile(r"^\s*(```|~~~)")
        broken = []
        for md in sorted(ROOT.glob("docs/**/*.md")) + [ROOT / "README.md"]:
            if not md.is_file():
                continue
            in_fence = False
            for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
                if fence_re.match(line):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                for target in link_re.findall(line):
                    t = target.strip()
                    if t.startswith(("http://", "https://", "#", "mailto:")):
                        continue
                    path_part = t.split("#", 1)[0].strip()
                    if not path_part:
                        continue
                    if not (md.parent / path_part).resolve().exists():
                        broken.append(f"{md.relative_to(ROOT)} -> {path_part}")
        self.assertEqual(broken, [], f"失效的相对链接: {broken}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
