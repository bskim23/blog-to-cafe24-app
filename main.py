import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from bs4 import BeautifulSoup

# [설정 정보]
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')
API_VERSION = "2025-12-01"

def get_access_token():
    print("🔑 [단계 1/5] 인증 토큰 갱신 중...")
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    
    try:
        res = requests.post(url, headers=headers, data=data)
        res.raise_for_status()
        result = res.json()
        
        # 새 리프레시 토큰이 발급되면 GitHub 환경 변수에 기록 시도
        new_refresh = result.get('refresh_token')
        if new_refresh and os.getenv('GITHUB_ENV'):
            with open(os.getenv('GITHUB_ENV'), "a") as f:
                f.write(f"NEW_REFRESH_TOKEN={new_refresh}\n")
        
        print("✅ 인증 성공")
        return result.get('access_token')
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        return None

def write_post_trace(access_token):
    # --- [단계 2] 원본 본문 크롤링 ---
    print("\n🧼 [단계 2/5] 네이버 블로그 원본 데이터 추출 중...")
    rss_url = "https://rss.blog.naver.com/mediheally_lab.xml"
    try:
        rss_res = requests.get(rss_url)
        rss_res.encoding = 'utf-8'
        item = ET.fromstring(rss_res.text).find('.//item')
        origin_url = item.find('link').text
        
        # 아이프레임 우회 주소 생성
        log_no = origin_url.split('/')[-1]
        real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
        
        blog_res = requests.get(real_url)
        soup = BeautifulSoup(blog_res.text, 'html.parser')
        main_container = soup.select_one('.se-main-container') or soup.select_one('#post-view')
        
        if not main_container:
            print("⚠️ 본문 영역을 찾을 수 없습니다.")
            return

        # 이미지 추출 (본문 내 pstatic 서버 이미지만 Max 5)
        raw_imgs = [img.get('src') or img.get('data-lazy-src') for img in main_container.find_all('img')]
        img_urls = [url for url in raw_imgs if url and 'postfiles.pstatic.net' in url][:5]
        
        title = item.find('title').text
        content = main_container.get_text(separator='<br>')
        print(f"   > 제목 확인: {title[:20]}...")
        print(f"   > 이미지 {len(img_urls)}개 포착")
    except Exception as e:
        print(f"❌ 데이터 추출 에러: {e}")
        return

    # --- [단계 3] 이미지 첨부 파일 처리 ---
    print("\n📸 [단계 3/5] 이미지 5개 첨부 파일 변환 중...")
    attachments = []
    for i, url in enumerate(img_urls):
        try:
            print(f"   [{i+1}/5] 다운로드: {url[:30]}...")
            img_res = requests.get(url, timeout=10)
            if img_res.status_code == 200:
                img_b64 = base64.b64encode(img_res.content).decode('utf-8')
                attachments.append({
                    "filename": f"medilly_attach_{i+1}.jpg",
                    "file_data": img_b64
                })
                print(f"      ✅ 변환 완료 ({len(img_b64)} bytes)")
        except:
            print(f"      ⚠️ {i+1}번 이미지 실패")

    # --- [단계 4/5] 카페24 전송 패키지 조립 ---
    if not attachments:
        print("❌ 첨부할 이미지가 없습니다. 갤러리 게시판 등록 불가.")
        return

    payload = {
        "shop_no": 1,
        "request": {
            "title": f"{title} ({datetime.now().strftime('%H:%M:%S')})",
            "content": content + f'<br><br><a href="{origin_url}">원문 보기</a>',
            "writer": "pp1125",
            "writer_name": "관리자",
            "password": "Wkmg12345678!",
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments,
            "file_count": len(attachments)
        }
    }

    # --- [단계 5/5] 최종 전송 및 상세 분석 ---
    print("\n📤 [단계 5/5] 카페24 서버로 전송 중...")
    api_url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    print(f"📊 전송 결과: {response.status_code}")
    if response.status_code == 201:
        print("🎉 [최종 성공] 게시글이 이미지와 함께 등록되었습니다!")
    else:
        print(f"❌ [실패 원인]: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        write_post_trace(token)
    else:
        print("🚨 인증 토큰이 없어 실행을 중단합니다.")
