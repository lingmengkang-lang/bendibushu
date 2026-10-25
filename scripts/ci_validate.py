#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ci_validate.py — local-offline-assistant 仓库结构校验（零第三方依赖）

用途：
  - GitHub Actions 的 validate job（ubuntu-latest 云端 runner）调用
  - CNB 云端流水线（python 镜像）调用
  - 本机手动执行：python scripts/ci_validate.py

检查项（全部只读，不修改仓库）：
  1) 关键文件 / 目录存在性
  2) SCADA TOP5 品牌文档齐备
  3) requirements.txt 可解析（不安装，仅校验格式）
  4) config/rag.config.json 是合法 JSON
  5) .ps1 脚本带 UTF-8 BOM（PowerShell 5.1 中文防乱码要求）
  6) Markdown 中的相对链接目标存在（粗粒度，忽略外链与锚点）

退出码：0 = 全部通过（允许 WARN）；1 = 存在 FAIL
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "README.md",
    "requirements.txt",
    "config/ollama-models.txt",
    "config/ollama-vision-model.txt",
    "config/rag.config.json",
    "docs/deploy/HANDOFF.md",
    "scripts/rag_manager.py",
    "scripts/start.ps1",
    "scripts/stop.ps1",
    "scripts/selfcheck.ps1",
    "scripts/setup_ollama.ps1",
    "scripts/launcher.ps1",
    "deploy/install.ps1",
    "deploy/package.ps1",
    "app/webui.py",
    "启动.bat",
    "停止.bat",
    "docs/plc/SAFETY.md",
    "docs/plc/brands.md",
    "docs/plc/hmi_scada_host.md",
    "docs/plc/how_to_extend.md",
    "docs/plc/image_parsing.md",
    "docs/plc/brand_onboarding_template.md",
]

# 组态软件使用率 TOP5（详见 docs/scada/README.md）
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
]

results = []  # (level, message)


def check(cond, ok_msg, fail_msg, level="FAIL"):
    if cond:
        results.append(("PASS", ok_msg))
    else:
        results.append((level, fail_msg))


def main() -> int:
    # ---------- 1. 文件 / 目录 ----------
    for rel in REQUIRED_DIRS:
        check((ROOT / rel).is_dir(), f"目录存在: {rel}", f"缺少目录: {rel}")
    for rel in REQUIRED_FILES + TOP5_DOCS:
        check((ROOT / rel).is_file(), f"文件存在: {rel}", f"缺少文件: {rel}")

    # ---------- 2. requirements.txt ----------
    req = ROOT / "requirements.txt"
    if req.is_file():
        bad = []
        n = 0
        for i, line in enumerate(req.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            n += 1
            # 形如 包名[extra]>=1.0,<2.0  或 包名==1.2.3
            if not re.match(r"^[A-Za-z0-9._\-]+(\[[A-Za-z0-9._,\-]+\])?\s*[<>=!~]", s):
                bad.append(f"第 {i} 行无法识别: {s}")
        check(n > 0, f"requirements.txt 解析到 {n} 个依赖", "requirements.txt 没有任何有效依赖")
        for b in bad:
            results.append(("FAIL", f"requirements.txt {b}"))

    # ---------- 3. rag.config.json ----------
    cfg_path = ROOT / "config/rag.config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            check("chroma" in cfg and "collection" in cfg["chroma"],
                  "rag.config.json 结构完整（chroma.collection）",
                  "rag.config.json 缺少 chroma.collection")
        except Exception as e:
            results.append(("FAIL", f"rag.config.json 非法 JSON: {e}"))

    # ---------- 4. .ps1 必须带 BOM ----------
    for ps in sorted((ROOT / "scripts").glob("*.ps1")) + [ROOT / "deploy/install.ps1"]:
        if not ps.is_file():
            continue
        raw = ps.read_bytes()
        rel = ps.relative_to(ROOT)
        check(raw.startswith(b"\xef\xbb\xbf"),
              f"PS1 带 BOM: {rel}",
              f"PS1 缺少 UTF-8 BOM（PowerShell 5.1 中文会乱码）: {rel}")

    # ---------- 5. Markdown 相对链接（跳过代码块，避免把示例链接误报为失效） ----------
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    fence_re = re.compile(r"^\s*(```|~~~)")
    broken = 0
    checked = 0
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
                checked += 1
                if not (md.parent / path_part).resolve().exists():
                    broken += 1
                    results.append(("WARN", f"链接目标不存在: {md.relative_to(ROOT)} -> {path_part}"))
    results.append(("PASS", f"Markdown 相对链接检查 {checked} 处，失效 {broken} 处"))

    # ---------- 输出 ----------
    n_pass = n_warn = n_fail = 0
    for level, msg in results:
        if level == "PASS":
            n_pass += 1
        elif level == "WARN":
            n_warn += 1
        else:
            n_fail += 1
        print(f"[{level}] {msg}")

    print("")
    print(f"===== 校验汇总: PASS {n_pass} / WARN {n_warn} / FAIL {n_fail} =====")
    if n_fail:
        print("结论: 失败（修复 FAIL 项后重跑）")
        return 1
    print("结论: 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
