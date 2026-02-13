import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# 1. 환경변수 로드
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

def get_access_token():
    """토큰 갱신 및 새 리프레시 토큰 GITHUB_ENV 저장"""
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    
    try:
        response = requests.post(url, headers=headers, data=data)
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

def get_latest_rss(rss_url):
    """RSS 피드에서 최신 글 1개 추출"""
    print(f"📡 RSS 읽는 중: {rss_url}")
    try:
        response = requests.get(rss_url, timeout=10)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)
        item = root.find('.//item')
        if item is None: return None
        
        title = item.find('title').text
        link = item.find('link').text
        desc = item.find('description').text
        img = re.findall(r'<img[^>]+src="([^">]+)"', desc)
        
        return {
            "title": title, 
            "link": link, 
            "content": desc, 
            "img": img[0] if img else None
        }
    except Exception as e:
        print(f"❌ RSS 오류: {e}")
        return None

def upload_image_to_cafe24(access_token, image_url):
    """네이버 이미지를 카페24 서버로 세탁 업로드"""
    if not image_url: return None
    print(f"📸 이미지 업로드 시도: {image_url[:50]}...")
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        img_data = base64.b64encode(img_res.content).decode('utf-8')
        
        url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/images"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "requests": [{
                "image_data": img_data,
                "filename": f"rss_{datetime.now().strftime('%H%M%S')}.jpg"
            }]
        }
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 201:
            return res.json()['images'][0]['url']
        return None
    except:
        return None

def write_post(access_token, post_data, cafe_img_url):
    """갤러리 게시판 포스팅 및 결과 출력"""
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    display_img = cafe_img_url if cafe_img_url else "https://sample.cafe24.com/sample_image.jpg"
    content_html = f"""
    <div style="text-align:center;">
        <img src="{display_img}" style="max-width:100%; border:1px solid #eee;">
        <div style="text-align:left; margin-top:20px;">
            {post_data['content']}
            <br><br>
            <a href="{post_data['link']}" target="_blank">👉 네이버 원문 보기</a>
        </div>
    </div>
    """
    
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": board_no,
            "title": post_data['title'],
            "content": content_html,
            "writer": "관리자",
            "author_password": "wkmg_pass_1234",
            "is_notice": "F",
            "is_secret": "F",
            "article_type": "A",
            "use_image_hosting": "T"
        }
    }
    
    print(f"📡 카페24 전송 시작...")
    response = requests.post(url, headers=headers, json=payload)
    
    # [진단 핵심] 성공/실패 여부와 상관없이 모든 응답을 로그에 남김
    print(f"📢 HTTP 상태 코드: {response.status_code}")
    if response.status_code == 201:
        print("🎉 포스팅 성공!")
    else:
        print(f"❌ 상세 에러 내용: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        # pp1125 네이버 RSS 사용
        post = get_latest_rss("https://rss.blog.naver.com/pp1125.xml")
        if post:
            cafe_img = upload_image_to_cafe24(token, post['img'])
            write_post(token, post, cafe_img)
        else:
            print("⚠️ 최신 글 데이터 없음")
    else:
        print("❌ 인증 토큰 획득 실패")
        sys.exit(1)
