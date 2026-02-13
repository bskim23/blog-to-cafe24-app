import os
import sys
import requests
import base64
import json
from datetime import datetime

# GitHub Secrets
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

if not all([MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("❌ [오류] 필수 환경변수 누락")
    sys.exit(1)

def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }
    
    print("🔄 [1/2] 토큰 갱신 및 교체 시도...")
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ 토큰 갱신 실패: {e}")
        print(f"응답: {response.text}")
        return None

    result = response.json()
    new_access_token = result.get('access_token')
    new_refresh_token = result.get('refresh_token') # ★ 핵심: 새 토큰 받기
    
    if new_access_token:
        print("✅ 토큰 갱신 성공!")
        # 중요: 다음 실행을 위해 새 Refresh Token을 알려줌
        if new_refresh_token:
            print("\n" + "="*60)
            print("🚨 [중요] 아래 토큰을 복사해서 GitHub Secrets를 업데이트하세요!")
            print(f"NEW_REFRESH_TOKEN: {new_refresh_token}")
            print("="*60 + "\n")
        return new_access_token
    return None

def check_connection(access_token):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    print("📡 [2/2] 게시판 목록 조회 테스트...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        boards = response.json().get('boards', [])
        print(f"🎉 연결 성공! (게시판 {len(boards)}개 발견)")
        for b in boards:
            print(f"- [{b['board_no']}] {b['board_name']}")
        return True
    else:
        print(f"❌ API 호출 실패: {response.text}")
        return False

def main():
    print(f"🚀 시작: {datetime.now()}")
    token = get_access_token()
    if token and check_connection(token):
        print("\n✅ 전체 테스트 완료")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
