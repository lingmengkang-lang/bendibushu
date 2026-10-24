#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap.py — local-offline-assistant 跨平台一键部署入口（零第三方依赖）

与 deploy/install.ps1 等价，但用纯 Python 重写，因此 Linux / macOS / Windows 通用。
目标：**clone 仓库 + 一条命令 = 完全部署**，本机除 Python 3.10+ 外不预装任何东西。

用法（在工程根目录或任意目录执行均可，会自动定位工程根）：
    python deploy/bootstrap.py                标准部署（不自动装 Ollama，仅检测+引导）
    python deploy/bootstrap.py --install-ollama  额外尝试安装 Ollama（需联网/权限）
    python deploy/bootstrap.py --recreate-venv   删除并重建 venv（依赖重装）
    python deploy/bootstrap.py --dry-run         只打印将要做什么，不落盘（安全自检用）
    python deploy/bootstrap.py --skip-selfcheck  不调用自检

本脚本做什么：
    1) 检测 Python 3.10+
    2) 创建 venv 并安装 requirements.txt
    3) 初始化目录结构（data/chroma、data/knowledge_base/docs、logs、models、lora…）
    4) 检测 Ollama（可选安装；Ollama 引擎与模型体积大，默认交给脚本或 CI 自托管节点）
    5) 运行 selfcheck（Windows 上调 scripts/selfcheck.ps1；其他平台打印提示）

本脚本不做什么（刻意留给别的脚本/CI）：
    - 不拉取任何模型（由 scripts/setup_ollama.ps1 负责，或 GitHub/CNB 自托管节点自动执行）
    - 不注册自托管 runner / 构建节点（见 docs/deploy/ollama_setup.md）

幂等性：重复执行安全；已存在的 venv 默认跳过创建（除非 --recreate-venv）。
安全：不使用 eval/exec；所有外部命令通过列表参数交由 subprocess，不做 shell 拼接。
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 中文输出防乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent          # deploy/
ROOT = SCRIPT_DIR.parent                              # 工程根

DEFAULT_VENV_REL = "venv"
REQUIREMENTS_REL = "requirements.txt"

# 与 install.ps1 保持一致的目录骨架
DIRS_TO_CREATE = [
    "data/chroma",
    "data/knowledge_base/docs",
    "logs",
    "models",
    "lora/output",
    "lora/dataset/data",
]
GITKEEPS = [
    "data/knowledge_base/docs/.gitkeep",
    "lora/dataset/data/.gitkeep",
]


# ----------------------------------------------------------------------------
# 纯函数（便于单元测试，无副作用）
# ----------------------------------------------------------------------------
def parse_python_version(output: str):
    """从 `python --version` 输出解析 (major, minor)。失败返回 None。"""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", output or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def parse_requirements(text: str) -> list:
    """
    解析 requirements.txt 为 [{name, spec, raw}, ...]。
    仅做轻量语法识别（与 ci_validate.py 一致），不真正安装。
    返回所有非空、非注释行的解析结果；无法识别的行 spec 记为 "" 但 name 尽力提取。
    """
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # 去掉行内注释（# 之前）
        s = s.split("#", 1)[0].strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z0-9._\-]+)(\[[A-Za-z0-9._,\-]+\])?\s*([<>=!~].*)?$", s)
        if m:
            name = m.group(1)
            spec = (m.group(2) or "") + (m.group(3) or "")
        else:
            # 形如 -r other.txt / --extra-index-url 等非标准行，原样保留
            name = s.split()[0] if s.split() else s
            spec = ""
        out.append({"name": name, "spec": spec, "raw": s})
    return out


def required_dirs() -> list:
    return list(DIRS_TO_CREATE)


def required_gitkeeps() -> list:
    return list(GITKEEPS)


# ----------------------------------------------------------------------------
# 有副作用的步骤（受 --dry-run 控制）
# ----------------------------------------------------------------------------
def log(msg: str, level: str = "INFO") -> None:
    prefix = {
        "INFO": "[\033[0;36m==\033[0m]",
        "OK": "[\033[0;32mOK\033[0m]",
        "WARN": "[\033[0;33mWARN\033[0m]",
        "FAIL": "[\033[0;31mFAIL\033[0m]",
    }.get(level, "[INFO]")
    print(f"{prefix} {msg}")


def detect_python(min_major: int = 3, min_minor: int = 10, candidates=None) -> str:
    """
    检测 Python 解释器路径。优先用 sys.executable（若是 3.10+），
    否则依次尝试 candidates 中的命令。返回可用解释器路径，找不到返回 None。
    """
    if candidates is None:
        candidates = ["python3", "python", "py"]
    # 自身是否满足
    if sys.version_info[:2] >= (min_major, min_minor):
        return sys.executable
    for c in candidates:
        try:
            out = subprocess.run([c, "--version"], capture_output=True, text=True, timeout=10)
            if out.returncode != 0:
                continue
            ver = parse_python_version((out.stdout or "") + (out.stderr or ""))
            if ver and ver >= (min_major, min_minor):
                return c
        except Exception:
            continue
    return None


def ensure_dirs(root: Path, dry_run: bool = False) -> None:
    """创建目录骨架与 .gitkeep。dry_run 时只打印。"""
    for d in required_dirs():
        p = root / d
        if dry_run:
            log(f"(dry-run) 将创建目录: {d}")
            continue
        p.mkdir(parents=True, exist_ok=True)
    for g in required_gitkeeps():
        p = root / g
        if dry_run:
            log(f"(dry-run) 将创建占位: {g}")
            continue
        if not p.exists():
            p.touch()


def create_or_reuse_venv(venv_dir: Path, recreate: bool, dry_run: bool, py: str) -> Path:
    if recreate and venv_dir.exists():
        if dry_run:
            log(f"(dry-run) 将删除旧 venv: {venv_dir}")
        else:
            log(f"删除旧 venv: {venv_dir}")
            shutil.rmtree(venv_dir)
    if venv_dir.exists():
        log("venv 已存在，跳过创建（--recreate-venv 可重建）。", "WARN")
        return venv_dir
    if dry_run:
        log(f"(dry-run) 将创建 venv: {venv_dir}  (python={py})")
        return venv_dir
    log(f"创建 venv: {venv_dir}")
    rc = subprocess.run([py, "-m", "venv", str(venv_dir)]).returncode
    if rc != 0:
        log("venv 创建失败", "FAIL")
        sys.exit(1)
    return venv_dir


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_pip(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def install_requirements(venv_dir: Path, root: Path, dry_run: bool) -> None:
    pip = venv_pip(venv_dir)
    req = root / REQUIREMENTS_REL
    if dry_run:
        log(f"(dry-run) 将通过 {pip} 安装 -r {REQUIREMENTS_REL}")
        return
    log("升级 pip ...")
    subprocess.run([str(pip), "install", "--upgrade", "pip"], check=False)
    log("安装依赖（chromadb 等，耗时取决于网络）...")
    rc = subprocess.run([str(pip), "install", "-r", str(req)], check=False).returncode
    if rc != 0:
        log("依赖安装失败，请检查网络与 pip 源。", "FAIL")
        sys.exit(1)
    log("依赖安装完成。", "OK")


def is_ollama_installed() -> bool:
    exe = shutil.which("ollama")
    return exe is not None


def install_ollama(dry_run: bool) -> None:
    """按平台尝试安装 Ollama。默认不调用；仅在 --install-ollama 时执行。"""
    if is_ollama_installed():
        log(f"Ollama 已安装: {shutil.which('ollama')}", "OK")
        return
    if dry_run:
        log("(dry-run) 将尝试安装 Ollama（平台相关）")
        return
    system = platform.system().lower()
    log("尝试安装 Ollama（需要联网与相应权限）...")
    if system == "windows":
        # 优先 winget；失败再提示手动下载
        rc = subprocess.run(
            ["winget", "install", "--id", "Ollama.Ollama", "-e",
             "--accept-source-agreements", "--accept-package-agreements"],
            check=False,
        ).returncode
        if rc != 0:
            log("winget 安装失败，请手动下载: https://ollama.com/download", "WARN")
    elif system == "darwin":
        # macOS：官方安装脚本
        subprocess.run(
            ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
            check=False,
        )
    else:
        # Linux：官方安装脚本
        subprocess.run(
            ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
            check=False,
        )


def run_selfcheck(root: Path, dry_run: bool, skip: bool) -> int:
    if skip:
        log("跳过自检（--skip-selfcheck）。", "WARN")
        return 0
    ps = root / "scripts" / "selfcheck.ps1"
    if dry_run:
        log(f"(dry-run) 将运行自检: {ps}")
        return 0
    if os.name == "nt" and ps.exists():
        rc = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps)],
                            check=False).returncode
        return rc
    log("selfcheck.ps1 仅 Windows 可用；其他平台请手动确认 venv/依赖/Ollama。", "WARN")
    return 0


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="local-offline-assistant 跨平台一键部署")
    parser.add_argument("--install-ollama", action="store_true",
                        help="额外尝试安装 Ollama（需联网/权限）")
    parser.add_argument("--recreate-venv", action="store_true",
                        help="删除并重建 venv（依赖重装）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将要做什么，不落盘（安全自检用）")
    parser.add_argument("--skip-selfcheck", action="store_true",
                        help="不调用自检")
    parser.add_argument("--root", default=str(ROOT),
                        help="工程根目录（默认自动定位）")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    dry = args.dry_run

    print("===== local-offline-assistant 跨平台部署 =====")
    print(f"工程目录: {root}")
    if dry:
        print("[DRY-RUN] 仅预览，不会修改任何文件/环境。")
    print("")

    # 1) Python 检测
    py = detect_python()
    if not py:
        log("未检测到 Python 3.10+。请先安装（安装时勾选 Add to PATH）: https://www.python.org/downloads/", "FAIL")
        return 1
    ver = subprocess.run([py, "--version"], capture_output=True, text=True)
    log(f"Python 检测通过: {(ver.stdout or ver.stderr).strip()}", "OK")

    # 2) venv + 依赖
    venv_dir = root / DEFAULT_VENV_REL
    create_or_reuse_venv(venv_dir, args.recreate_venv, dry, py)
    install_requirements(venv_dir, root, dry)

    # 3) 目录结构
    log("初始化目录结构 ...")
    ensure_dirs(root, dry)

    # 4) Ollama 检测 / 可选安装
    log("检测 Ollama ...")
    if is_ollama_installed():
        log(f"Ollama 已安装: {shutil.which('ollama')}", "OK")
    elif args.install_ollama:
        install_ollama(dry)
    else:
        log("未检测到 Ollama。手动安装: https://ollama.com/download；"
            "或加 --install-ollama 让本脚本尝试安装；"
            "也可交给 GitHub/CNB 自托管节点自动装（见 docs/deploy/ollama_setup.md）。", "WARN")

    # 5) 自检
    sc = run_selfcheck(root, dry, args.skip_selfcheck)

    print("")
    print("===== 部署完成 =====")
    print("后续步骤（按顺序）：")
    print("  1) 安装 Ollama 引擎 + 拉取模型: scripts/setup_ollama.ps1 (Windows)；"
          "或交给 GitHub/CNB 自托管节点自动装（见 docs/deploy/ollama_setup.md）")
    print("  2) 启动服务:                    scripts/start.ps1 (Windows)")
    print("  3) 一键导入知识库:              python scripts/rag_manager.py add-all")
    print("  4) WorkBuddy 接入配置:          见 config/workbuddy/knowledge-base.md")
    print("  5) 增加应用场景（新品牌/新器件）: 见 docs/plc/how_to_extend.md")
    if sc != 0:
        log("自检存在 FAIL 项（见上），请先修复。", "FAIL")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
