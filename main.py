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
    return requests.post(url, headers=headers, data=data).json().get('access_token')

def get_latest_naver_post():
    rss_url = f"https://rss.blog.naver.com/{NAVER_BLOG_ID}.xml"
    res = requests.get(rss_url)
    # xml 파서가 없을 경우를 대비해 기본 파서를 쓰되, 구조를 더 정확히 짚도록 수정했습니다.
    soup = BeautifulSoup(res.content, 'html.parser') 
    item = soup.find('item')
    
    if item:
        # RSS 내부의 link는 태그 안에 텍스트로 존재하므로 명확히 추출합니다.
        post_link = item.find('link').next_sibling.strip() if item.find('link') else "URL 확인 불가"
        print(f"📍 타겟팅 URL: {post_link}")
        
        return {
            "title": item.find('title').get_text(),
            "description": item.find('description').get_text(),
            "link": post_link
        }
    return None

def run_fix_v3():
    token = get_access_token()
    post = get_latest_naver_post()
    if not token or not post: return print("❌ 데이터 로드 실패")

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2023-03-01"
    }
    
    # 본문 구성
    content_html = f"<div style='line-height:1.8;'>{post['description']}<br><br><a href='{post['link']}'>원문 보기</a></div>"
    
    payload = {
        "request": {
            "title": post['title'],
            "content": content_html,
            "author": "메디힐리"
        }
    }
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 201:
        print(f"✅ 드디어 성공! 파서 에러를 해결했습니다.")
    else:
        print(f"❌ 포스팅 실패: {res.json()}")

if __name__ == "__main__":
    run_fix_v3()
