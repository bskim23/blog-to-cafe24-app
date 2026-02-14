#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트 스크립트: 기본 환경 확인
"""

import sys
import os

# 즉시 flush
sys.stdout.flush()
sys.stderr.flush()

print("=" * 70, flush=True)
print("🔍 [TEST] 스크립트 시작", flush=True)
print("=" * 70, flush=True)
sys.stdout.flush()

print(f"\n📌 [TEST] Python 정보:", flush=True)
print(f"   버전: {sys.version}", flush=True)
print(f"   실행 파일: {sys.executable}", flush=True)
print(f"   작업 디렉토리: {os.getcwd()}", flush=True)
sys.stdout.flush()

print(f"\n📁 [TEST] 파일 확인:", flush=True)
files = os.listdir('.')
for f in sorted(files):
    print(f"   {f}", flush=True)
print(f"   main.py 존재: {os.path.exists('main.py')}", flush=True)
if os.path.exists('main.py'):
    size = os.path.getsize('main.py')
    print(f"   main.py 크기: {size:,} bytes", flush=True)
sys.stdout.flush()

print(f"\n🔐 [TEST] 환경변수 확인:", flush=True)
env_vars = [
    'CAFE24_MALL_ID',
    'CAFE24_CLIENT_ID', 
    'CAFE24_CLIENT_SECRET',
    'CAFE24_REFRESH_TOKEN',
    'PA_TOKEN',
    'GITHUB_REPOSITORY'
]
for var in env_vars:
    value = os.environ.get(var)
    if value:
        # 앞 10자만 표시
        display = value[:10] + '...' if len(value) > 10 else value
        print(f"   {var}: ✅ {display}", flush=True)
    else:
        print(f"   {var}: ❌ 없음", flush=True)
sys.stdout.flush()

print(f"\n📦 [TEST] 패키지 import 테스트:", flush=True)

packages = [
    ('requests', 'requests'),
    ('BeautifulSoup', 'bs4'),
    ('PyGithub', 'github'),
    ('xml.etree.ElementTree', 'xml.etree.ElementTree'),
    ('base64', 'base64'),
    ('json', 'json')
]

for name, module in packages:
    try:
        __import__(module)
        print(f"   ✅ {name}", flush=True)
    except Exception as e:
        print(f"   ❌ {name}: {e}", flush=True)
sys.stdout.flush()

print(f"\n🔍 [TEST] main.py 첫 10줄 미리보기:", flush=True)
try:
    with open('main.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()[:10]
        for i, line in enumerate(lines, 1):
            print(f"   {i}: {line.rstrip()}", flush=True)
except Exception as e:
    print(f"   ❌ 읽기 실패: {e}", flush=True)
sys.stdout.flush()

print(f"\n✅ [TEST] 테스트 완료!", flush=True)
print("=" * 70, flush=True)
sys.stdout.flush()
