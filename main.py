import os, requests, base64
from bs4 import BeautifulSoup

# [설정] 대표님 정보
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
MALL_ID = "pp1125"
NAVER_BLOG_ID = "mediheally_lab"

def get_access_token():
    try:
        url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
        auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}
        res = requests.post(url, headers=headers, data=data).json()
        return res.get('access_token')
    except Exception as e:
        print(f"토큰 갱신 중 오류: {e}")
        return None

def get_latest_naver_post():
    try:
        # RSS 방식은 별도의 파싱 라이브러리 없이도 가장 안정적입니다.
        rss_url = f"https://rss.blog.naver.com/{NAVER_BLOG_ID}.xml"
        res = requests.get(rss_url)
        # XML 파서 오류를 방지하기 위해 html.parser 대신 lxml 혹은 기본 파서 사용
        soup = BeautifulSoup(res.content, 'html.parser') 
        item = soup.find('item')
        if item:
            # RSS 내 description은 이미 HTML 형태입니다.
            return {
                "title": item.find('title').text,
                "description": item.find('description').text
            }
    except Exception as e:
        print(f"네이버 블로그 로드 중 오류: {e}")
    return None

def run_strategy_b():
    token = get_access_token()
    post = get_latest_naver_post()
    
    if not token:
        return print("❌ Access Token을 가져오지 못했습니다. Secrets를 확인하세요.")
    if not post:
        return print("❌ 네이버 블로그 글을 가져오지 못했습니다.")

    # 카페24 포스팅 API (게시판 8번)
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2023-03-01"
    }
    
    payload = {
        "request": {
            "title": post['title'],
            "content": post['description'],
            "author": "메디힐리"
        }
    }
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 201:
        print(f"✅ 성공: [{post['title']}] 업로드 완료!")
    else:
        print(f"❌ 포스팅 실패: {res.text}")

if __name__ == "__main__":
    run_strategy_b()
