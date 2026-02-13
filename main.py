import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from bs4 import BeautifulSoup

# [인증 정보]
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

def get_access_token():
    """
    [절대 원칙] 토큰 갱신을 가장 먼저 수행하고, 
    성공 즉시 다음 실행을 위한 리프레시 토큰을 로그에 출력함.
    """
    print("\n🔑 [단계 1] 인증 토큰 갱신 시도...")
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }
    
    try:
        res = requests.post(url, headers=headers, data=data)
        
        if res.status_code != 200:
            print(f"❌ 토큰 갱신 실패! 상세 사유: {res.text}")
            return None, None
            
        result = res.json()
        access_token = result.get('access_token')
        new_refresh = result.get('refresh_token')
        
        # [Fail-Safe] 성공하자마자 로그에 새 토큰을 박아버림 (포스팅 에러 대비)
        print("\n" + "="*60)
        print("✅ 토큰 갱신 성공!")
        print(f"⚠️ 다음 실행을 위해 깃허브 Secrets(CAFE24_REFRESH_TOKEN)를 아래 값으로 업데이트하세요:")
        print(f"👉 {new_refresh}")
        print("="*60 + "\n")
        
        return access_token, new_refresh
    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
        return None, None

def write_post_logic(access_token):
    """실제 포스팅 및 크롤링 로직"""
    print("📡 [단계 2] 원본 데이터 크롤링 및 이미지 추출 시작...")
    rss_url = "https://rss.blog.naver.com/mediheally_lab.xml"
    
    # 1. RSS에서 원본 링크 추출
    rss_res = requests.get(rss_url)
    rss_res.encoding = 'utf-8'
    item = ET.fromstring(rss_res.text).find('.//item')
    origin_url = item.find('link').text
    
    # 2. 본문 크롤링 (배너 제외)
    log_no = origin_url.split('/')[-1]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
    soup = BeautifulSoup(requests.get(real_url).text, 'html.parser')
    container = soup.select_one('.se-main-container') or soup.select_one('#post-view')
    
    # 3. 이미지 추출 (본문 내 pstatic 서버 이미지만 Max 5)
    raw_imgs = [img.get('src') or img.get('data-lazy-src') for img in container.find_all('img')]
    img_urls = [url for url in raw_imgs if url and 'postfiles.pstatic.net' in url][:5]
    
    # 4. 이미지 첨부파일 변환
    attachments = []
    for i, url in enumerate(img_urls):
        try:
            print(f"📸 이미지 {i+1}/5 처리 중...")
            img_res = requests.get(url, timeout=10)
            img_b64 = base64.b64encode(img_res.content).decode('utf-8')
            attachments.append({
                "filename": f"medilly_img_{i+1}.jpg",
                "file_data": img_b64
            })
        except: continue

    if not attachments:
        print("❌ 이미지 없음. 전송 중단.")
        return

    # 5. 최종 전송
    payload = {
        "shop_no": 1,
        "request": {
            "title": f"{item.find('title').text} ({datetime.now().strftime('%H:%M:%S')})",
            "content": container.get_text(separator='<br>') + f'<br><br><a href="{origin_url}">원문 보기</a>',
            "writer": "pp1125",
            "writer_name": "관리자",
            "password": "Wkmg12345678!",
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments,
            "file_count": len(attachments)
        }
    }
    
    api_url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    print(f"📊 최종 결과: {response.status_code}")
    if response.status_code != 201:
        print(f"❌ 실패 사유: {response.text}")

if __name__ == "__main__":
    # 1. 토큰부터 무조건 갱신
    access_token, new_refresh = get_access_token()
    
    # 2. 갱신에 성공했다면 포스팅 시도
    if access_token:
        try:
            write_post_logic(access_token)
        except Exception as e:
            print(f"❌ 포스팅 도중 오류 발생: {e}")
            print("💡 하지만 토큰은 이미 갱신되었습니다. 로그 상단의 새 토큰을 Secrets에 업데이트하세요.")
