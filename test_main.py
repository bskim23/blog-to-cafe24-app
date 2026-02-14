#!/usr/bin/env python3
import sys
import os

print("=" * 70, flush=True)
print("🔍 TEST 시작", flush=True)
print("=" * 70, flush=True)
sys.stdout.flush()

print(f"\nPython 버전: {sys.version}", flush=True)
print(f"작업 디렉토리: {os.getcwd()}", flush=True)
print(f"main.py 존재 여부: {os.path.exists('main.py')}", flush=True)

print("\n환경변수 확인:", flush=True)
print(f"CAFE24_MALL_ID: {'✅' if os.environ.get('CAFE24_MALL_ID') else '❌'}", flush=True)
print(f"CAFE24_CLIENT_ID: {'✅' if os.environ.get('CAFE24_CLIENT_ID') else '❌'}", flush=True)

print("\nimport 테스트:", flush=True)
try:
    import requests
    print("✅ requests", flush=True)
except Exception as e:
    print(f"❌ requests: {e}", flush=True)

try:
    from bs4 import BeautifulSoup
    print("✅ BeautifulSoup", flush=True)
except Exception as e:
    print(f"❌ BeautifulSoup: {e}", flush=True)

try:
    from github import Github, Auth
    print("✅ PyGithub", flush=True)
except Exception as e:
    print(f"❌ PyGithub: {e}", flush=True)

print("\n✅ 테스트 완료!", flush=True)
sys.stdout.flush()
