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

# 필수 정보가 없으면 바로 종료 (디버깅용)
if not all([MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("❌ [오류] 필수 환경변수(Secrets)가 누락되었습니다.")
    print(f"- MALL_ID: {MALL_ID}")
    print(f"- CLIENT_ID: {'OK' if CLIENT_ID else 'Missing'}")
    print(f"- CLIENT_SECRET: {'OK' if CLIENT_SECRET else 'Missing'}")
    print(f"- REFRESH_TOKEN: {'OK' if REFRESH_TOKEN else 'Missing'}")
    sys.exit(1)

# ==============================================================================
# 2. 핵심: 토큰 갱신 함수 (이게 401 에러를 해결합니다!)
# ==============================================================================
def get_access_token():
    """
    Refresh Token을 사용해 새 Access Token을 발급받습니다.
    (Cafe24 규격인 Basic Auth 헤더를 정확히 생성합니다.)
    """
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    
    # 1. Client ID와 Secret을 'ID:Secret' 형태로 합치고 Base64로 암호화
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_str.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    # 2. 헤더에 'Basic 암호문'을 넣어서 전송 (중요!)
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
        response.raise_for_status() # 에러 발생 시 예외 처리
    except requests.exceptions.RequestException as e:
        print(f"❌ 토큰 갱신 실패: {e}")
        print(f"응답 내용: {response.text if 'response' in locals() else '응답 없음'}")
        return None

    result = response.json()
    new_access_token = result.get('access_token')
    
    if new_access_token:
        print("✅ 토큰 갱신 성공!")
        return new_access_token
    else:
        print("❌ 응답에 access_token이 없습니다.")
        return None

# ==============================================================================
# 3. 테스트: 게시판 목록 조회 (연동 확인용)
# ==============================================================================
def check_connection(access_token):
    """
    발급받은 토큰으로 API가 잘 호출되는지 테스트합니다.
    """
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2024-06-01"
    }
    
    print("📡 [2/2] API 연결 테스트 (게시판 목록 조회)...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        boards = response.json().get('boards', [])
        print(f"🎉 연결 성공! (발견된 게시판 수: {len(boards)}개)")
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
    
    # 1. 토큰 갱신
    access_token = get_access_token()
    if not access_token:
        sys.exit(1)
        
    # 2. 연결 확인 (성공하면 이후에 글쓰기 로직을 추가하면 됩니다)
    if check_connection(access_token):
        print("\n✅ 모든 시스템이 정상입니다. 이제 글을 올릴 준비가 되었습니다.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
