import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# 1. 환경변수 및 고정값
MALL_ID = os.environ.get('CAFE24_MALL_ID') # pp1125
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')
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
    except:
        return None

def get_latest_rss(rss_url):
    print(f"📡 RSS 읽기: {rss_url}")
    try:
        response = requests.get(rss_url, timeout=15)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)
        item = root.find('.//item')
        if item is None: return None
        title = item.find('title').text
        link = item.find('link').text
        desc = item.find('description').text
        img = re.findall(r'<img[^>]+src="([^">]+)"', desc)
        return {"title": title, "link": link, "content": desc, "img": img[0] if img else None}
    except Exception as e:
        print(f"❌ RSS 오류: {e}")
        return None

def upload_image_to_cafe24(access_token, image_url):
    """404 에러 해결을 위해 버전 헤더 필수 포함"""
    if not image_url: return None
    print(f"📸 이미지 업로드 중: {image_url[:50]}...")
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        img_data = base64.b64encode(img_res.content).decode('utf-8')
        url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/images"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Cafe24-Api-Version": API_VERSION
        }
        payload = {"requests": [{"image_data": img_data, "filename": f"rss_{datetime.now().strftime('%H%M%S')}.jpg"}]}
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 201:
            return res.json()['images'][0]['url']
        print(f"⚠️ 이미지 업로드 실패 상세: {res.text}")
        return None
    except:
        return None

def write_post(access_token, post_data, cafe_img_url):
    """422 에러 해결: 클로드 제안 반영 + 필수 필드 보강"""
    print("📡 게시판 전송 시작...")
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }
    
    # 본문 구성 (이미지를 최상단에 배치)
    img_tag = f'<div style="text-align:center;"><img src="{cafe_img_url}" style="max-width:100%;"></div><br>' if cafe_img_url else ""
    content_html = f'{img_tag}{post_data["content"]}<br><br><a href="{post_data["link"]}" target="_blank">👉 원문 보기</a>'
    
    # [최종 페이로드]
    payload = {
        "shop_no": 1,
        "request": {
            "title": post_data['title'],
            "content": content_html,
            "writer": "pp1125", # ✅ 카페24 관리자 ID
            "is_notice": "F",
            "is_secret": "F",
            "category_no": 0, # ✅ 갤러리형 필수값 (0으로 지정)
            "author_password": "wkmg_pass_1234" # ✅ 안전하게 포함
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Status Code: {response.status_code}")
    if response.status_code == 201:
        print(f"🎉 성공: {post_data['title']}")
        return True
    else:
        print(f"❌ 실패 상세: {response.text}")
        return False

if __name__ == "__main__":
    token = get_access_token()
    if token:
        # ✅ 네이버 블로그 ID: mediheally_lab
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            cafe_img = upload_image_to_cafe24(token, post['img'])
            write_post(token, post, cafe_img or post['img'])
    else:
        sys.exit(1)
