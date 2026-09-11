#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import datetime

class LogRedirector:
    def __init__(self, log_folder="logs"):
        self.today_str = datetime.datetime.now().strftime('%Y%m%d')
        self.log_dir = os.path.join(log_folder, self.today_str)
        os.makedirs(self.log_dir, exist_ok=True)

        self.terminal = sys.stdout
        timestamp = datetime.datetime.now().strftime('%H%M%S')
        self.log_path = os.path.join(self.log_dir, f"{timestamp}.log")
        self.log_file = open(self.log_path, 'a', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        if self.log_file:
            self.log_file.write(message)
            self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        if self.log_file:
            self.log_file.flush()

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.terminal
        if self.log_file:
            print(f"\n📄 本次运行日志已保存至: {self.log_path}")
            self.log_file.close()