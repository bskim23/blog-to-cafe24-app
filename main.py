import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# 환경변수 로드
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

# API 공통 설정
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
    except:
        return None

def upload_image_to_cafe24(access_token, image_url):
    """404 에러 해결: 버전 헤더 추가"""
    if not image_url: return None
    print("📸 [단계 3] 이미지 업로드 중 (버전 헤더 적용)...")
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        img_data = base64.b64encode(img_res.content).decode('utf-8')
        url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/images"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Cafe24-Api-Version": API_VERSION # 버전 누락 해결
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
    """422 에러 해결: 필수 필드 보강"""
    print("📡 [단계 4] 게시판 전송 시작 (필수 필드 보강)...")
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }
    
    # 갤러리형 필수: 이미지를 본문 최상단에 배치
    display_img = cafe_img_url if cafe_img_url else "https://sample.cafe24.com/sample_image.jpg"
    content_html = f'<div style="text-align:center;"><img src="{display_img}" style="max-width:100%;"><br><br></div>{post_data["content"]}'
    
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": board_no, # 본문 내 중복 명시 (필수)
            "title": post_data['title'],
            "content": content_html,
            "writer": "admin", # 실제 관리자 ID로 시도
            "author_password": "wkmg_pass_1234",
            "is_notice": "F",
            "is_secret": "F"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print(f"🎉 드디어 성공! : {post_data['title']}")
    else:
        print(f"❌ 최종 실패 ({response.status_code}): {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            # 1. 이미지 업로드 시도
            cafe_img = upload_image_to_cafe24(token, post['img'])
            # 2. 이미지 업로드 성공 여부와 상관없이 글쓰기 시도 (단, 업로드 실패 시 원본 링크 사용)
            write_post(token, post, cafe_img or post['img'])
    else:
        sys.exit(1)
