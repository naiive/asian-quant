#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import functools

def retry(max_retries=3, delay=2):
    """通用重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"⚠️ [重试] {func.__name__} 失败 (第 {attempt}/{max_retries} 次): {e}")
                    if attempt < max_retries:
                        time.sleep(delay)
            print(f"❌ [失败] {func.__name__} 超过最大重试次数")
            raise last_exception
        return wrapper
    return decorator

def timer(func):
    """函数耗时统计装饰器"""
    def wrapper(*args, **kwargs):
        t1 = time.time()
        result = func(*args, **kwargs)
        t2 = time.time()
        print(f"⏱️ [性能] {func.__name__} 耗时: {t2 - t1:.1f} s")
        return result
    return wrapper