import os, requests, base64
from bs4 import BeautifulSoup

# [설정] 대표님 정보
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
MALL_ID = "pp1125"
NAVER_BLOG_ID = "mediheally_lab"

def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(url, headers=headers, data=data).json()
    return res.get('access_token')

def get_latest_naver_post():
    rss_url = f"https://rss.blog.naver.com/{NAVER_BLOG_ID}.xml"
    res = requests.get(rss_url)
    # 이제 lxml이 설치되었으므로 가장 정확한 'xml' 파서를 사용합니다.
    soup = BeautifulSoup(res.content, 'xml') 
    item = soup.find('item')
    
    if item:
        # RSS 내부 데이터를 깨끗하게 추출
        return {
            "title": item.title.get_text(),
            "description": item.description.get_text(),
            "link": item.link.get_text()
        }
    return None

def run_final():
    token = get_access_token()
    post = get_latest_naver_post()
    
    # 데이터 로드 확인용 로그
    if not token: return print("❌ 토큰 발급 실패")
    if not post: return print("❌ 네이버 글 로드 실패")
    
    print(f"📍 대상 포스팅: {post['title']}")

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2023-03-01"
    }
    
    # 전략 B: 가독성 높인 본문 구성
    content_html = f"<div style='line-height:1.8; font-size:15px;'>{post['description']}</div>"
    
    payload = {
        "request": {
            "title": post['title'],
            "content": content_html,
            "author": "메디힐리"
        }
    }
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 201:
        print(f"✅ [성공] 느낌연구소에 '{post['title']}' 등록 완료!")
    else:
        print(f"❌ 포스팅 실패 상세: {res.json()}")

if __name__ == "__main__":
    run_final()
