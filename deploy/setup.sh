#!/usr/bin/env bash
# ============================================================================
# setup.sh — local-offline-assistant 部署便捷入口（Linux / macOS）
#
# 等价于 Windows 上的 deploy/install.ps1，但调用跨平台的 deploy/bootstrap.py。
# 前置：本机已装 Python 3.10+（仓库不自带运行时，这是唯一外部依赖）。
#
# 用法：
#   ./deploy/setup.sh                  标准部署
#   ./deploy/setup.sh --install-ollama 额外尝试安装 Ollama
#   ./deploy/setup.sh --recreate-venv  重建 venv（依赖重装）
#   ./deploy/setup.sh --dry-run        只预览不做任何改动（安全自检）
#
# 设计目标：clone 仓库 + 一条命令 = 完全部署，本机不预装除 Python 外的任何东西。
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 选择 Python 解释器
PY=""
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "[FAIL] 未检测到 python3/python，请先安装 Python 3.10+（https://www.python.org/downloads/）"
  exit 1
fi

echo "工程根目录: $ROOT"
echo "Python    : $($PY --version 2>&1)"
echo ""

exec "$PY" "$ROOT/deploy/bootstrap.py" "$@"
