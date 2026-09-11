#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
from pathlib import Path

def reset_git_history(branch_name="main", commit_message="AI code commit"):

    project_root = Path(__file__).resolve().parent.parent.parent

    os.chdir(project_root)

    if not (project_root / ".git").exists():
        print(f"❌ [错误] {project_root} 未找到.git目录")
        return

    commands = [
        ["git", "checkout", "--orphan", "latest_branch"],
        ["git", "add", "-A"],
        ["git", "commit", "-m", commit_message],
        ["git", "branch", "-D", branch_name],
        ["git", "branch", "-m", branch_name],
        ["git", "push", "-f", "origin", branch_name]
    ]

    print(f"🚀 [重置] {project_root} 仓库历史根目录")

    try:
        for cmd in commands:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(f"STDOUT: {result.stdout.strip()}")

        print(f"\n✅ [成功] 推送远程 {branch_name} 分支")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ [错误] {' '.join(e.cmd)}")
        print(f"错误输出: {e.stderr}")
    except Exception as e:
        print(f"❌ [错误] {e}")


if __name__ == "__main__":
    reset_git_history()