import os, requests, base64
from bs4 import BeautifulSoup

# [설정] 대표님 정보
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
MALL_ID = "pp1125"

def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(url, headers=headers, data=data).json()
    return res.get('access_token')

def run_auto_post():
    token = get_access_token()
    if not token:
        print("❌ 토큰 발급 실패. Secrets 설정을 확인하세요.")
        return

    # 전략 B: 이미지 처리 및 포스팅 로직이 들어갈 자리입니다.
    # 우선 연결이 성공했는지 테스트용 게시글을 올립니다.
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2023-03-01"
    }
    payload = {
        "request": {
            "title": "GitHub Actions 자동화 가동 테스트 (전략 B)",
            "content": "이미지 자동 업로드를 포함한 전략 B 시스템이 정상 가동 중입니다.",
            "author": "관리자"
        }
    }
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 201:
        print("🚀 축하합니다! 무인 공장이 첫 제품(포스팅)을 생산했습니다.")
    else:
        print(f"❌ 포스팅 실패: {res.json()}")

if __name__ == "__main__":
    run_auto_post()
