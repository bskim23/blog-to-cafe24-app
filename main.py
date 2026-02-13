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
    
    print("🔄 [1/2] 토큰 갱신 시도 중...")
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        result = response.json()
        new_refresh = result.get('refresh_token')
        if new_refresh:
            env_file = os.getenv('GITHUB_ENV')
            if env_file:
                with open(env_file, "a") as f:
                    f.write(f"NEW_REFRESH_TOKEN={new_refresh}\n")
        return result.get('access_token')
    except Exception as e:
        print(f"❌ 토큰 갱신 실패: {e}")
        return None

def write_post(access_token):
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"}
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": board_no,
            "title": f"🚀 최종 통합 테스트 성공 ({datetime.now().strftime('%H:%M:%S')})",
            "content": "<p>모든 설정이 완료되었습니다. 무한 동력이 가동됩니다.</p>",
            "author_password": "wkmg_pass_1234",
            "is_secret": "F"
        }
    }
    print(f"📡 [2/2] 느낌연구소 글쓰기 시도...")
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print("🎉 게시글 작성 성공!")
    else:
        print(f"❌ 실패: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token: write_post(token)
    else: sys.exit(1)
