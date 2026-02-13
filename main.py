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
    [422 에러 최종 해결 전략]
    1. 제목 중복 방지: 제목 뒤에 현재 시각 추가 (카페24 중복 체크 우회)
    2. 필드명 정밀화: 관리자 포스팅이므로 'writer' 필드에 ID 'pp1125' 사용
    3. 첨부파일 강제화: 매뉴얼 규정대로 attachments 배열 필수 포함
    """
    print("📡 [게시판] 갤러리 규격 전송 시작...")
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    
    # 이미지 파일 데이터 생성
    attachments = []
    if post_data['img']:
        try:
            img_res = requests.get(post_data['img'], headers={'User-Agent': 'Mozilla/5.0'})
            img_base64 = base64.b64encode(img_res.content).decode('utf-8')
            attachments.append({
                "filename": f"gallery_{datetime.now().strftime('%H%M%S')}.jpg",
                "file_data": img_base64
            })
        except: pass

    if not attachments:
        print("❌ 이미지가 없어 갤러리 게시판 등록이 불가능합니다.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }

    # [매뉴얼 기반 최종 페이로드]
    payload = {
        "shop_no": 1,
        "request": {
            # 중복 포스팅 방지를 위해 제목에 시각 추가
            "title": f"{post_data['title']} ({datetime.now().strftime('%H:%M:%S')})",
            "content": post_data['content'] + f'<br><br><a href="{post_data["link"]}">원문보기</a>',
            "writer": "pp1125", # 관리자 ID 직접 사용
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 결과 코드: {response.status_code}")
    if response.status_code == 201:
        print(f"🎉 성공! 게시판을 확인하세요.")
    else:
        print(f"❌ 실패 상세: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            write_post_gallery(token, post)
