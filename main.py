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
    """
    Refresh Token을 사용해 Access Token을 갱신하고,
    새로 발급된 Refresh Token을 GitHub Actions 환경변수로 내보냅니다.
    """
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    
    # Base64 인코딩 (Basic Auth)
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
    
    # ★ [핵심] 새 토큰이 나오면 깃허브 액션(YAML)에게 전달
    if new_refresh_token:
        print("✅ 새 Refresh Token 발급 완료")
        
        # GITHUB_ENV 파일에 기록하면, 다음 단계(YAML)에서 ${{ env.NEW_REFRESH_TOKEN }}으로 쓸 수 있음
        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh_token}\n")
            print("📝 깃허브 환경변수에 새 토큰 등록 완료 (자동 저장 대기)")
        else:
            print("⚠️ 로컬 테스트 환경입니다. (자동 저장 건너뜀)")
            print(f"새 토큰(수동 저장 필요): {new_refresh_token}")
            
    return new_access_token

# ==============================================================================
# 3. 글쓰기 함수 (느낌연구소: 8번)
# ==============================================================================
def write_post(access_token):
    board_no = 8  # 느낌연구소 게시판 ID
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    # 게시글 내용 작성
    payload = {
        "request": {
            "title": f"🚀 자동화 포스팅 테스트 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
            "content": "<p>이 글은 깃허브 액션(GitHub Actions)을 통해 자동으로 작성되었습니다.</p><p>토큰 자동 갱신 시스템이 정상 작동 중입니다.</p>",
            "author": "관리자"
        }
    }
    
    print(f"📡 [2/2] 게시글 작성 시도 (게시판 ID: {board_no})...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print("🎉 게시글 작성 성공!")
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
    
    # 필수 변수 체크
    if not all([MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ [오류] 필수 환경변수(Secrets)가 누락되었습니다.")
        sys.exit(1)

    # 1. 토큰 갱신 (및 새 토큰 전달)
    access_token = get_access_token()
    
    # 2. 글쓰기 실행
    if access_token:
        if write_post(access_token):
            print("\n✅ 모든 작업이 성공적으로 완료되었습니다.")
        else:
            sys.exit(1)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
