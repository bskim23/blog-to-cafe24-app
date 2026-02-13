import os, requests, base64
from bs4 import BeautifulSoup

# [설정] 대표님 정보
CLIENT_ID = os.environ.get('CLIENT_ID', '').strip()
CLIENT_SECRET = os.environ.get('CLIENT_SECRET', '').strip()
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN', '').strip()
MALL_ID = "pp1125"
NAVER_BLOG_ID = "mediheally_lab"

def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    
    # 1. Basic Auth 헤더 생성 (공식 가이드 방식)
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # 2. 전송 데이터 구성
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }
    
    # 3. 요청 및 응답 확인
    res = requests.post(url, headers=headers, data=payload)
    
    if res.status_code == 200:
        return res.json().get('access_token')
    else:
        # 실패 시 로그를 남겨 원인을 파악합니다.
        print(f"❌ 카페24 서버 응답 에러 ({res.status_code}): {res.text}")
        return None

def run_final():
    token = get_access_token()
    if not token:
        return # 실패 로그는 위에서 출력됨

    # 네이버 RSS 데이터 가져오기 (lxml 활용)
    try:
        rss_url = f"https://rss.blog.naver.com/{NAVER_BLOG_ID}.xml"
        res = requests.get(rss_url)
        soup = BeautifulSoup(res.content, 'xml')
        item = soup.find('item')
        
        if not item:
            return print("❌ 네이버 블로그 글을 찾을 수 없습니다.")

        post_title = item.title.get_text()
        post_content = item.description.get_text()
        
        # 카페24 게시판 포스팅
        post_url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
        post_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Cafe24-Api-Version": "2023-03-01"
        }
        
        payload = {
            "request": {
                "title": post_title,
                "content": f"<div style='line-height:1.8; font-size:15px;'>{post_content}</div>",
                "author": "메디힐리"
            }
        }
        
        post_res = requests.post(post_url, json=payload, headers=post_headers)
        if post_res.status_code == 201:
            print(f"✅ [대성공] 느낌연구소에 '{post_title}' 등록 완료!")
        else:
            print(f"❌ 포스팅 실패 상세: {post_res.json()}")
            
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    run_final()
