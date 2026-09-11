#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from cryptography.fernet import Fernet

os.environ['TERM'] = os.environ.get('TERM', 'xterm-256color')

C_BLUE = "\033[38;5;75m"
C_CYAN = "\033[38;5;123m"
C_GREEN = "\033[38;5;84m"
C_YELLOW = "\033[38;5;227m"
C_RED = "\033[38;5;203m"
C_GRAY = "\033[38;5;244m"
C_BOLD = "\033[1m"
C_END = "\033[0m"

try:
    from conf.config import ENCRYPTION_KEY
except ImportError:
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

def draw_header():
    print(f"\n{C_BLUE}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{C_END}")
    print(
        f"                 {C_BOLD}{C_CYAN}CIPHER-BOT SECURITY TERMINAL{C_END} ")
    print(f"{C_BLUE}┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫{C_END}")
    key_display = str(ENCRYPTION_KEY)[:5] + "..." if ENCRYPTION_KEY else "UNDEFINED"
    print(
        f"          {C_GRAY}ENCRYPTION KEY:{C_END} {C_YELLOW}{key_display}{C_END}  {C_GRAY}| STATUS:{C_END} {C_GREEN}ACTIVE{C_END} ")
    print(f"{C_BLUE}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{C_END}")
    print(
        f"{C_BOLD}   操作{C_END}: {C_GREEN}e <text>{C_END} 加密  │  {C_YELLOW}d <token>{C_END} 解密  │  {C_RED}c{C_END} 清屏  │  {C_RED}q{C_END} 退出")
    print(f" {C_GRAY}────────────────────────────────────────────────────────────{C_END}")


def run_tool():
    if not ENCRYPTION_KEY:
        print(f"{C_RED}❌ 找不到 ENCRYPTION_KEY，请检查配置！{C_END}")
        return

    key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
    cipher = Fernet(key)

    os.system('cls' if os.name == 'nt' else 'clear')
    draw_header()

    while True:
        try:
            prompt = f"{C_BOLD}{C_CYAN}❯{C_END} "
            print()
            raw_input = input(prompt).strip()

            if not raw_input:
                continue

            cmd_lower = raw_input.lower()
            if cmd_lower == 'q': break
            if cmd_lower == 'c':
                os.system('cls' if os.name == 'nt' else 'clear')
                draw_header()
                continue

            parts = raw_input.split(maxsplit=1)
            if len(parts) < 2:
                print(f" {C_RED}⚠ 语法错误：请使用 e/d 指令开头{C_END}")
                continue

            mode, content = parts[0].lower(), parts[1]

            if mode == 'e':
                res = cipher.encrypt(content.encode()).decode()
                print(f"{C_GREEN}🔐ENCRYPTED ❯❯❯{C_END}")
                print(f"{C_BOLD}{res}{C_END}")
            elif mode == 'd':
                res = cipher.decrypt(content.encode()).decode()
                print(f"{C_YELLOW}🔓DECRYPTED ❯❯❯{C_END}")
                print(f"{C_BOLD}{C_CYAN}{res}{C_END}")
            else:
                print(f"{C_RED}❌ 无效指令模式: {mode}{C_END}")

        except Exception as e:
            print(f" {C_RED}💥 失败: {str(e)}{C_END}")


if __name__ == "__main__":
    try:
        run_tool()
    except (KeyboardInterrupt, EOFError):
        print(f"\n\n{C_YELLOW}👋 系统已安全离线{C_END}")
        sys.exit()