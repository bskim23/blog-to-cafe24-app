import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from bs4 import BeautifulSoup

# [설정]
MALL_ID = os.environ.get('CAFE24_MALL_ID') # pp1125
API_VERSION = "2025-12-01"

def write_post_trace(access_token):
    # --- [단계 1] RSS 힌트로 원본 링크 확보 ---
    print("\n🔍 [1/5] RSS 파싱 및 원본 링크 추출 중...")
    rss_url = "https://rss.blog.naver.com/mediheally_lab.xml"
    res = requests.get(rss_url)
    res.encoding = 'utf-8'
    item = ET.fromstring(res.text).find('.//item')
    origin_url = item.find('link').text
    print(f"   > 타겟 URL: {origin_url}")

    # --- [단계 2] 원본 본문 크롤링 (배너/광고 제외) ---
    print("\n🧼 [2/5] 본문 세척 및 이미지 추출 중...")
    log_no = origin_url.split('/')[-1]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
    blog_soup = BeautifulSoup(requests.get(real_url).text, 'html.parser')
    main_container = blog_soup.select_one('.se-main-container')
    
    img_urls = []
    if main_container:
        # 본문 내 이미지 중 네이버 포스트 서버 이미지만 최대 5개 추출
        raw_imgs = [img.get('src') or img.get('data-lazy-src') for img in main_container.find_all('img')]
        img_urls = [url for url in raw_imgs if url and 'postfiles.pstatic.net' in url][:5]
    print(f"   > 본문 이미지 {len(img_urls)}개 포착 (Max 5)")

    # --- [단계 3] 파일 다운로드 및 Base64 변환 (파일 상태 검증) ---
    print("\n📸 [3/5] 이미지 첨부 파일 처리 중 (Max 5)...")
    attachments = []
    for i, url in enumerate(img_urls):
        try:
            print(f"   [{i+1}/5] 다운로드 시도: {url[:40]}...")
            img_res = requests.get(url, timeout=10)
            if img_res.status_code == 200:
                # 파일 크기 확인 (너무 크면 카페24가 거부함)
                size_kb = len(img_res.content) / 1024
                img_b64 = base64.b64encode(img_res.content).decode('utf-8')
                attachments.append({
                    "filename": f"attach_file_{i+1}.jpg",
                    "file_data": img_b64
                })
                print(f"      ✅ 완료: attach_file_{i+1}.jpg ({size_kb:.1f} KB)")
            else:
                print(f"      ⚠️ 실패: HTTP {img_res.status_code}")
        except Exception as e:
            print(f"      ❌ 에러: {e}")

    # --- [단계 4] 페이로드 조립 (매뉴얼 규격 준수) ---
    print("\n📦 [4/5] 카페24 전송 패키지 조립 중...")
    if not attachments:
        print("   ❌ 중단: 첨부할 이미지가 하나도 없습니다. (갤러리 필수 조건 위반)")
        return

    payload = {
        "shop_no": 1,
        "request": {
            "title": f"{item.find('title').text} ({datetime.now().strftime('%H:%M:%S')})",
            "content": main_container.get_text(separator='<br>') if main_container else "내용 없음",
            "writer": "pp1125",
            "writer_name": "관리자",
            "password": "Wkmg12345678!",
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments,
            "file_count": len(attachments) # 매뉴얼 명시 필드
        }
    }
    print(f"   > 최종 데이터 구성 완료 (첨부파일 {len(attachments)}개 포함)")

    # --- [단계 5] 카페24 API 전송 및 에러 분석 ---
    print("\n📤 [5/5] 카페24 서버로 최종 전송 중...")
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/8/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"📊 [결과 리포트]")
    print(f"   - 상태 코드: {response.status_code}")
    if response.status_code == 201:
        print("   - 🎉 결과: 성공적으로 등록되었습니다!")
    else:
        print(f"   - ❌ 결과: 실패")
        print(f"   - 상세 사유: {response.text}") # 422 에러의 구체적 이유를 카페24가 말해줍니다.

if __name__ == "__main__":
    # 토큰 획득 로직은 동일 (생략)
    token = get_access_token() 
    if token: write_post_trace(token)
