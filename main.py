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
# 2. 토큰 갱신 함수 (최우선 실행)
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
    
    print("🔄 [1/2] 토큰 갱신 시도 (최우선 작업)...")
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status() # 400, 401 에러 즉시 감지
    except Exception as e:
        print(f"❌ 토큰 갱신 단계에서 치명적 오류: {e}")
        print(f"응답 내용: {response.text if 'response' in locals() else 'No response'}")
        return None

    result = response.json()
    new_access_token = result.get('access_token')
    new_refresh_token = result.get('refresh_token')
    
    # ★ [생존 코드] 받자마자 깃허브 시스템에 등록
    if new_refresh_token:
        print("✅ 새 Refresh Token 확보 완료")
        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh_token}\n")
            print("📝 [안전장치] 새 토큰을 저장 대기열에 등록했습니다. (글쓰기 실패해도 저장됨)")
            
    return new_access_token

# ==============================================================================
# 3. 글쓰기 함수 (수정됨: writer, shop_no 적용)
# ==============================================================================
def write_post(access_token):
    board_no = 8  # 느낌연구소 게시판 ID
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    # payload 수정: author -> writer, shop_no 추가
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": board_no,
            "title": f"🚀 자동화 포스팅 성공! ({datetime.now().strftime('%H:%M:%S')})",
            "content": "<p>대표님, 드디어 성공입니다! 토큰도 갱신되고 글도 써졌습니다.</p>",
            "writer": "관리자" 
        }
    }
    
    print(f"📡 [2/2] 게시글 작성 시도...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print("🎉 게시글 작성 성공! (HTTP 201)")
        return True
    else:
        # 글쓰기가 실패해도 프로그램은 죽지만, 위에서 등록한 토큰은 YAML이 살려줍니다.
        print(f"❌ 글쓰기 실패 (HTTP {response.status_code})")
        print(f"에러 메시지: {response.text}")
        return False

# ==============================================================================
# 4. 메인 실행
# ==============================================================================
def main():
    if not all([MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ 필수 환경변수 누락")
        sys.exit(1)

    # 1. 토큰 갱신 (가장 먼저!)
    access_token = get_access_token()
    
    if access_token:
        # 2. 글쓰기 시도
        if write_post(access_token):
            print("\n✅ 모든 작업 성공")
        else:
            print("\n⚠️ 글쓰기는 실패했지만, 토큰은 갱신되었습니다.")
            sys.exit(1) # 에러로 종료하더라도 YAML의 if: always()가 토큰을 저장함
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
