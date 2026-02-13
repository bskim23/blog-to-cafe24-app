# ----------------------------------------------------------------------
# [1] 사용자 입력 구역 (여기에 토큰을 붙여넣으세요)
# ----------------------------------------------------------------------
CURRENT_REFRESH_TOKEN = "oeJFFd1qYykHVU0VriTTuE"

# 고정값 (대표님 설정 반영 완료)
MALL_ID = "pp1125"
CLIENT_ID = "ehqlhLOUAaBKXGu4QBqFQA"
CLIENT_SECRET = "CJdrn0ZHNpnktekO7oF96B"
BOARD_NO = 8               # 갤러리 게시판
PASSWORD = "1234"          # 비번 고정
RSS_URL = "https://rss.blog.naver.com/mediheally_lab.xml"
# ----------------------------------------------------------------------

import requests
import base64
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime

def run_main_process():
    # 1. 토큰 갱신 (가장 먼저 수행)
    print(f"📡 [1/4] 토큰 갱신 및 확보 중...")
    
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": CURRENT_REFRESH_TOKEN
    }

    try:
        res = requests.post(url, headers=headers, data=data)
        if res.status_code != 200:
            print(f"❌ 토큰 갱신 실패: {res.text}")
            print("💡 팁: 리프레시 토큰은 한 번 쓰면 버려집니다. 방금 발급받은 최신 토큰인지 확인하세요.")
            return

        token_data = res.json()
        new_access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')

        # [중요] 새 토큰 즉시 출력
        print("\n" + "="*60)
        print("✅ [성공] 토큰 갱신 완료! (이걸 꼭 저장하세요)")
        print(f"👉 다음 실행용 새 REFRESH_TOKEN:\n{new_refresh_token}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
        return

    # 2. RSS 크롤링
    print(f"📡 [2/4] 네이버 블로그 최신 글 가져오는 중...")
    rss_res = requests.get(RSS_URL)
    rss_item = ET.fromstring(rss_res.text).find('.//item')
    post_title = rss_item.find('title').text
    post_link = rss_item.find('link').text
    
    # 네이버 스마트에디터 원본 URL 추출 로직
    log_no = post_link.split('/')[-1]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
    
    soup = BeautifulSoup(requests.get(real_url).text, 'html.parser')
    # 본문 컨테이너 찾기 (se-main-container or post-view)
    content_area = soup.select_one('.se-main-container') or soup.select_one('#post-view')
    
    if not content_area:
        print("❌ 본문을 찾을 수 없습니다.")
        return

    # 3. 이미지 추출 (최대 5개)
    print(f"📸 [3/4] 이미지 추출 및 변환 중 (Max 5개)...")
    img_tags = content_area.find_all('img')
    attachments = []
    
    for idx, img in enumerate(img_tags):
        if idx >= 5: break # 5개 제한
        src = img.get('src') or img.get('data-lazy-src')
        if src and 'postfiles.pstatic.net' in src:
            # 이미지 다운로드 및 Base64 인코딩
            img_data = requests.get(src).content
            b64_img = base64.b64encode(img_data).decode()
            attachments.append({
                "filename": f"image_{idx+1}.jpg",
                "file_data": b64_img
            })

    # 4. 카페24 업로드
    print(f"📤 [4/4] 카페24 {BOARD_NO}번 게시판에 업로드 중...")
    
    # 본문 HTML 정리 (이미지는 제거하고 텍스트만 + 원문 링크)
    clean_content = content_area.get_text(separator='<br>') + f'<br><br><a href="{post_link}" target="_blank">원문 보러가기</a>'
    
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": BOARD_NO,
            "title": post_title,
            "content": clean_content,
            "writer": "관리자",
            "password": PASSWORD,  # 1234
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments
        }
    }

    api_url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    headers = {
        "Authorization": f"Bearer {new_access_token}",
        "Content-Type": "application/json"
    }

    post_res = requests.post(api_url, headers=headers, json=payload)
    
    if post_res.status_code == 201:
        print("\n🎉 [최종 성공] 게시글이 정상적으로 등록되었습니다!")
        print(f"🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/")
    else:
        print(f"❌ 등록 실패: {post_res.text}")

# 실행
run_main_process()
