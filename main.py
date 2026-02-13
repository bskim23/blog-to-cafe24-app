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
    # 네이버 RSS는 'xml' 파서로 읽어야 링크가 깨지지 않습니다.
    soup = BeautifulSoup(res.content, 'xml') 
    item = soup.find('item')
    
    if item:
        # 깨진 URL이 아닌 진짜 link 텍스트만 추출
        original_link = item.find('link').text.strip()
        print(f"📍 추출된 진짜 URL: {original_link}")
        
        return {
            "title": item.find('title').text,
            "description": item.find('description').text,
            "link": original_link
        }
    return None

def run_fix_v2():
    token = get_access_token()
    post = get_latest_naver_post()
    
    if not token or not post: return print("❌ 데이터 로드 실패")

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2023-03-01"
    }
    
    # 전략 B: 원본 링크를 하단에 추가하여 '상세보기' 연결 보장
    content_html = f"""
    <div style='font-family:sans-serif; line-height:1.8;'>
        {post['description']}
        <br><br>
        <p><a href='{post['link']}' target='_blank' style='color:#007bff;'>👉 네이버 블로그에서 원문 보기</a></p>
    </div>
    """
    
    payload = {
        "request": {
            "title": post['title'],
            "content": content_html,
            "author": "메디힐리"
        }
    }
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 201:
        print(f"✅ 드디어 성공! URL 오류를 수정하여 게시했습니다.")
    else:
        print(f"❌ 포스팅 실패 상세: {res.json()}")

if __name__ == "__main__":
    run_fix_v2()
