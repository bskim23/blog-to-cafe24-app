import os
import sys
import requests
import base64
import json
from datetime import datetime

# ==============================================================================
# 1. GitHub Secrets 환경변수 가져오기
# ==============================================================================
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

# 필수 정보 체크
if not all([MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("❌ [오류] 필수 환경변수(Secrets)가 누락되었습니다.")
    sys.exit(1)

# ==============================================================================
# 2. 토큰 갱신 함수 (로그인)
# ==============================================================================
def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    
    # 헤더 생성 (Base64)
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_str.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }
    
    print("🔄 [1/2] 토큰 갱신 시도 중...")
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 토큰 갱신 실패: {e}")
        return None

    return response.json().get('access_token')

# ==============================================================================
# 3. 테스트: 게시판 목록 조회 (버전 수정됨!)
# ==============================================================================
def check_connection(access_token):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        # ▼▼▼ 여기가 수정되었습니다 (2025-12-01) ▼▼▼
        "X-Cafe24-Api-Version": "2025-12-01" 
    }
    
    print("📡 [2/2] API 연결 테스트 (게시판 목록 조회)...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        boards = response.json().get('boards', [])
        print(f"🎉 연결 성공! (발견된 게시판 수: {len(boards)}개)")
        # 게시판 ID 확인용 출력
        for b in boards:
            print(f"- 게시판 이름: {b['board_name']}, ID: {b['board_no']}")
        return True
    else:
        print(f"❌ API 호출 실패 (HTTP {response.status_code})")
        print(f"에러 메시지: {response.text}")
        return False

# ==============================================================================
# 4. 메인 실행
# ==============================================================================
def main():
    print(f"🚀 스크립트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    access_token = get_access_token()
    if not access_token:
        sys.exit(1)
        
    if check_connection(access_token):
        print("\n✅ 모든 테스트 통과! 이제 글쓰기 기능을 추가하면 됩니다.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
