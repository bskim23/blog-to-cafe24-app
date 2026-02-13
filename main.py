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
API_VERSION = "2025-12-01"

def get_access_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    try:
        res = requests.post(url, headers=headers, data=data)
        result = res.json()
        new_refresh = result.get('refresh_token')
        if new_refresh and os.getenv('GITHUB_ENV'):
            with open(os.getenv('GITHUB_ENV'), "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh}\n")
        return result.get('access_token')
    except: return None

def get_latest_rss(rss_url):
    print(f"📡 [RSS] 읽기: {rss_url}")
    try:
        res = requests.get(rss_url, timeout=15)
        res.encoding = 'utf-8'
        root = ET.fromstring(res.text)
        item = root.find('.//item')
        if item is None: return None
        title = item.find('title').text
        link = item.find('link').text
        desc = item.find('description').text
        img_match = re.search(r'<img[^>]+src="([^">]+)"', desc)
        return {"title": title, "link": link, "content": desc, "img": img_match.group(1) if img_match else None}
    except: return None

def write_post_gallery(access_token, post_data):
    """
    [매뉴얼 기반 422 해결 전략]
    1. attachments 배열에 이미지 파일 데이터(Base64) 필수 포함
    2. 필드명 수정: writer -> writer_name, author_password -> password
    """
    print("📡 [게시판] 첨부파일 포함 전송 시작...")
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }

    # 이미지 첨부 처리 (Base64 변환)
    attachments = []
    if post_data['img']:
        try:
            img_res = requests.get(post_data['img'], headers={'User-Agent': 'Mozilla/5.0'})
            img_base64 = base64.b64encode(img_res.content).decode('utf-8')
            attachments.append({
                "filename": f"thumb_{datetime.now().strftime('%H%M%S')}.jpg",
                "file_data": img_base64
            })
        except Exception as e:
            print(f"⚠️ 이미지 변환 실패: {e}")

    # 갤러리 게시판은 첨부파일이 없으면 422 에러가 발생하므로 체크
    if not attachments:
        print("❌ 갤러리 게시판은 이미지가 필수입니다. 전송을 중단합니다.")
        return

    payload = {
        "shop_no": 1,
        "request": {
            "title": post_data['title'],
            "content": post_data['content'] + f'<br><br><a href="{post_data["link"]}">원문보기</a>',
            "writer_name": "관리자", # 매뉴얼 명시 필드
            "password": "Wkmg12345678!", # 매뉴얼 명시 필드
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments # 핵심: 실제 파일 데이터 첨부
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 결과 코드: {response.status_code}")
    if response.status_code == 201:
        print(f"🎉 드디어 성공! : {post_data['title']}")
    else:
        print(f"❌ 실패 상세: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            write_post_gallery(token, post)
    else:
        sys.exit(1)
