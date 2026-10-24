#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_ci_validate.py — 在真实仓库上运行 scripts/ci_validate.py，断言其通过。

零依赖（只调用子进程），验证"仓库结构校验"这一 CI 门禁本身可正确执行。
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class CiValidateTests(unittest.TestCase):

    def test_ci_validate_passes_on_real_repo(self):
        proc = subprocess.run(
            [sys.executable, "scripts/ci_validate.py"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"ci_validate.py 返回非 0:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        # 至少要看到汇总行
        self.assertIn("校验汇总", proc.stdout, "ci_validate.py 未输出汇总行")


if __name__ == "__main__":
    unittest.main(verbosity=2)
