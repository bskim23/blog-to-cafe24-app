import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime

MALL_ID = os.environ.get('CAFE24_MALL_ID') # pp1125
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

# 카페24 강제 최신 버전
API_VERSION = "2025-12-01"

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
    except: return None

def get_latest_rss(rss_url):
    print(f"📡 [RSS] 읽기: {rss_url}")
    try:
        response = requests.get(rss_url, timeout=15)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)
        item = root.find('.//item')
        if item is None: return None
        title = item.find('title').text
        link = item.find('link').text
        desc = item.find('description').text
        img_match = re.search(r'<img[^>]+src="([^">]+)"', desc)
        first_img = img_match.group(1) if img_match else None
        return {"title": title, "link": link, "content": desc, "img": first_img}
    except: return None

def write_post(access_token, post_data):
    """
    [422 해결 필살기]
    1. 비밀번호 필드 추가 (UI 규칙 준수)
    2. 카테고리 번호 명시 (기본값 0)
    3. 작성자명 단순화
    """
    print("📡 [게시판] 전송 시작...")
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }
    
    # 본문 구성 (HTML 정리)
    content_html = ""
    if post_data['img']:
        content_html += f'<p style="text-align:center;"><img src="{post_data["img"]}" style="max-width:100%;"></p>'
    content_html += f'{post_data["content"]}<br><br><p><a href="{post_data["link"]}" target="_blank">👉 원문 보기</a></p>'

    # 422 에러를 방지하는 최적의 페이로드 구조
    payload = {
        "shop_no": 1,
        "request": {
            "title": post_data['title'],
            "content": content_html,
            "writer": "관리자", # ID 대신 이름으로 전송
            "category_no": 0,  # 카테고리 미사용이라도 0으로 명시
            "author_password": "Wkmg12345678!", # UI 규칙(대소문자+숫자+특수문자) 준수 더미 비번
            "is_notice": "F",
            "is_secret": "F"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 결과 코드: {response.status_code}")
    
    if response.status_code == 201:
        print(f"🎉 성공: {post_data['title']}")
    else:
        print(f"❌ 실패 상세: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            write_post(token, post)
    else:
        sys.exit(1)
