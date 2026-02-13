# main.py 전체 덮어쓰기
import os
import sys
import requests
import base64
import json
from datetime import datetime

MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    
    print("🔄 토큰 갱신 시도...")
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ 토큰 갱신 실패: {e}")
        return None

    result = response.json()
    new_refresh = result.get('refresh_token')
    
    # ★ 새 토큰 저장 대기
    if new_refresh:
        print("✅ 새 토큰 확보 완료")
        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh}\n")
    
    return result.get('access_token')

def write_post(access_token):
    # writer 항목 삭제하고 필수 항목만 남김 (422 에러 해결)
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"}
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": "8",
            "title": f"🚀 자동 포스팅 성공 ({datetime.now().strftime('%H:%M:%S')})",
            "content": "<p>대표님, 드디어 모든 설정이 끝났습니다! 이제 무한동력입니다.</p>"
        }
    }
    
    print("📡 게시글 작성 시도...")
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print("🎉 작성 성공!")
        return True
    else:
        print(f"❌ 작성 실패: {response.text}")
        return False

if __name__ == "__main__":
    if not all([MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        sys.exit(1)
    
    token = get_access_token()
    if token:
        write_post(token)
    else:
        sys.exit(1)
