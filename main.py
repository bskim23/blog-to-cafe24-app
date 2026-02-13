import os, requests, base64

# GitHub Secrets에서 가져온 정보
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

def run_test_post():
    token = get_access_token()
    if not token:
        print("❌ 토큰 발급 실패. Secrets 설정을 확인하세요.")
        return

    # 게시판 8번에 가동 축하 메시지를 올립니다.
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2023-03-01"
    }
    payload = {
        "request": {
            "title": "🚀 무인 자동화 공장 가동 성공!",
            "content": "이 글은 대표님의 Mac mini가 꺼진 상태에서 GitHub Actions가 올린 글입니다.",
            "author": "김봉수"
        }
    }
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 201:
        print("✅ 성공! 카페24 게시판을 확인해 보세요.")
    else:
        print(f"❌ 실패: {res.json()}")

if __name__ == "__main__":
    run_test_post()
