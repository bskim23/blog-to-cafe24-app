import os
import sys
import requests
import base64
import json
from datetime import datetime

# ==============================================================================
# 1. 환경변수 가져오기
# ==============================================================================
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

# ==============================================================================
# 2. 토큰 갱신 및 깃허브 전달 함수
# ==============================================================================
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
    
    print("🔄 [1/2] 토큰 갱신 시도 중...")
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ 토큰 갱신 실패: {e}")
        print(f"응답 내용: {response.text}")
        return None

    result = response.json()
    new_access_token = result.get('access_token')
    new_refresh_token = result.get('refresh_token')
    
    if new_refresh_token:
        print("✅ 새 Refresh Token 발급 완료")
        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh_token}\n")
            print("📝 깃허브 환경변수에 새 토큰 등록 완료")
            
    return new_access_token

# ==============================================================================
# 3. 글쓰기 함수 (수정됨: writer 필드 적용)
# ==============================================================================
def write_post(access_token):
    board_no = 8  # 느낌연구소 게시판 ID
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    # payload 수정: author -> writer
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": board_no,
            "title": f"🚀 자동화 포스팅 성공! ({datetime.now().strftime('%H:%M:%S')})",
            "content": "<p>대표님, 드디어 성공입니다! 토큰도 갱신되고 글도 써졌습니다.</p>",
            "writer": "관리자" 
        }
    }
    
    print(f"📡 [2/2] 게시글 작성 시도 (게시판 ID: {board_no})...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201: # 201 Created
        print("🎉 게시글 작성 성공! (HTTP 201)")
        return True
    else:
        print(f"❌ 글쓰기 실패 (HTTP {response.status_code})")
        print(f"에러 메시지: {response.text}")
        return False

# ==============================================================================
# 4. 메인 실행
# ==============================================================================
def main():
    print(f"🚀 스크립트 시작: {datetime.now()}")
    
    if not all([MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ 필수 환경변수 누락")
        sys.exit(1)

    access_token = get_access_token()
    
    if access_token:
        # 토큰 갱신 성공하면 글쓰기 시도
        if write_post(access_token):
            print("\n✅ 미션 컴플리트: 토큰 갱신 + 글쓰기 모두 성공")
        else:
            # 글쓰기 실패해도 토큰은 갱신되었으므로 성공으로 간주 (다음 턴을 위해)
            sys.exit(1) 
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
