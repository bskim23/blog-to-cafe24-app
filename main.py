import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# 1. 환경변수
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
        res = requests.post(url, headers=headers, data=data)
        result = res.json()
        new_refresh = result.get('refresh_token')
        if new_refresh and os.getenv('GITHUB_ENV'):
            with open(os.getenv('GITHUB_ENV'), "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh}\n")
        return result.get('access_token')
    except: return None

def get_latest_rss(rss_url):
    print(f"📡 RSS 읽기: {rss_url}")
    try:
        res = requests.get(rss_url, timeout=15)
        res.encoding = 'utf-8'
        root = ET.fromstring(res.text)
        item = root.find('.//item')
        if item is None: return None
        
        desc = item.find('description').text
        # 본문에서 모든 이미지 주소 추출 (최대 5개 제한)
        all_imgs = re.findall(r'<img[^>]+src="([^">]+)"', desc)
        
        return {
            "title": item.find('title').text,
            "link": item.find('link').text,
            "content": desc,
            "imgs": all_imgs[:5] # 최대 5개만 추출
        }
    except: return None

def write_post_gallery(access_token, post_data):
    """
    [최종 규격 반영]
    1. 최대 5개 이미지 추출 및 Base64 인코딩
    2. 매뉴얼 명시 필드: file_count, writer_name, password 추가
    3. UI 간섭 방지: 순수 POST 요청으로 '새 글 작성' 강제
    """
    print(f"📡 게시판 전송 (최대 5개 이미지 추출 및 {len(post_data['imgs'])}개 처리)...")
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    # 1. attachments 배열 구성 (최대 5개)
    attachments = []
    for i, img_url in enumerate(post_data['imgs']):
        try:
            img_res = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            img_base64 = base64.b64encode(img_res.content).decode('utf-8')
            attachments.append({
                "filename": f"gallery_img_{i+1}.jpg",
                "file_data": img_base64
            })
        except: continue

    if not attachments:
        print("❌ 첨부할 이미지가 없어 전송이 불가능합니다.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }

    # 2. 페이로드 구성 (매뉴얼 정밀 반영)
    payload = {
        "shop_no": 1,
        "request": {
            "title": f"{post_data['title']} ({datetime.now().strftime('%H:%M:%S')})",
            "content": post_data['content'],
            "writer_name": "pp1125",
            "password": "Wkmg12345678!",
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments,
            "file_count": len(attachments) # 매뉴얼 명시 필드 추가
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 결과 코드: {response.status_code}")
    if response.status_code == 201:
        print(f"🎉 성공! {len(attachments)}개의 이미지가 포함된 새 글이 작성되었습니다.")
    else:
        print(f"❌ 실패 상세: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        # 네이버 블로그: mediheally_lab
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            write_post_gallery(token, post)
