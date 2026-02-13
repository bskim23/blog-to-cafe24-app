import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# 1. 환경변수 로드
MALL_ID = os.environ.get('CAFE24_MALL_ID') # pp1125
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

# 가장 범용적인 안정 버전
API_VERSION = "2024-03-01"

def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        new_refresh = result.get('refresh_token')
        if new_refresh and os.getenv('GITHUB_ENV'):
            with open(os.getenv('GITHUB_ENV'), "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh}\n")
        return result.get('access_token')
    except:
        return None

def get_latest_rss(rss_url):
    print(f"📡 [RSS] 읽기 시도: {rss_url}")
    try:
        response = requests.get(rss_url, timeout=15)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)
        item = root.find('.//item')
        if item is None: return None
        
        title = item.find('title').text
        link = item.find('link').text
        desc = item.find('description').text
        # 본문에서 첫 번째 이미지 추출
        img_match = re.search(r'<img[^>]+src="([^">]+)"', desc)
        first_img = img_match.group(1) if img_match else None
        
        return {"title": title, "link": link, "content": desc, "img": first_img}
    except Exception as e:
        print(f"❌ RSS 오류: {e}")
        return None

def write_post(access_token, post_data):
    """
    [최후의 전략] 
    1. 비밀번호 제거 
    2. 이미지 업로드 생략 (네이버 원본 링크 사용) 
    3. 필수 필드 최소화
    """
    print("📡 [게시판] 전송 시작...")
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }
    
    # 본문 구성 (이미지 포함)
    content_html = ""
    if post_data['img']:
        content_html += f'<div style="text-align:center;"><img src="{post_data["img"]}" style="max-width:100%;"></div><br>'
    content_html += f'{post_data["content"]}<br><br><a href="{post_data["link"]}" target="_blank">원문 보기</a>'

    # [초간결 페이로드] 카페24 관리자 포스팅 최소 규격
    payload = {
        "shop_no": 1,
        "request": {
            "title": post_data['title'],
            "content": content_html,
            "writer": "pp1125", # 카페24 ID
            "is_notice": "F",
            "is_secret": "F"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 결과 코드: {response.status_code}")
    
    if response.status_code == 201:
        print(f"🎉 성공: {post_data['title']}")
    else:
        print(f"❌ 실패 사유: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        # 네이버 블로그: mediheally_lab
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            write_post(token, post)
    else:
        print("❌ 토큰 획득 실패")
        sys.exit(1)
