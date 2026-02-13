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
    soup = BeautifulSoup(res.content, 'xml') # XML 파서 사용
    item = soup.find('item')
    
    if item:
        post_link = item.find('link').text
        post_title = item.find('title').text
        # 로그에 정확한 타겟 URL 출력
        print(f"\n🔎 [분석 중] 네이버 최신글 발견!")
        print(f"📌 제목: {post_title}")
        print(f"🔗 주소: {post_link}\n")
        
        return {
            "title": post_title,
            "description": item.find('description').text,
            "link": post_link
        }
    return None

def run_strategy_b():
    token = get_access_token()
    post = get_latest_naver_post()
    
    if not token or not post:
        return print("❌ 데이터 로드 실패 (토큰 또는 블로그 확인 필요)")

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2023-03-01"
    }
    
    # 레이아웃 최적화
    content_html = f"<div style='font-family:sans-serif; line-height:1.8;'>{post['description']}</div>"
    
    payload = {
        "request": {
            "title": post['title'],
            "content": content_html,
            "author": "메디힐리"
        }
    }
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 201:
        print(f"✅ [성공] 느낌연구소(8번)에 포스팅 완료!")
    else:
        print(f"❌ [실패] 에러 내용: {res.json()}")

if __name__ == "__main__":
    run_strategy_b()
