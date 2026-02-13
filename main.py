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
    print("🔑 [단계 1/5] 인증 토큰 갱신 시도 중...")
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    try:
        res = requests.post(url, headers=headers, data=data)
        res.raise_for_status()
        print("✅ 인증 성공")
        return res.json().get('access_token')
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        return None

def write_post_trace(access_token):
    print("\n📡 [단계 2/5] 네이버 RSS 데이터 추출 시작...")
    rss_url = "https://rss.blog.naver.com/mediheally_lab.xml"
    try:
        res = requests.get(rss_url, timeout=10)
        res.encoding = 'utf-8'
        root = ET.fromstring(res.text)
        item = root.find('.//item')
        
        # [상세 로그: 제목]
        title = item.find('title').text
        print(f"📝 제목 확인: {title[:30]}...")
        
        # [상세 로그: 내용]
        content = item.find('description').text
        print(f"📄 내용 추출 완료 (글자 수: {len(content)}자)")
        
        # [상세 로그: 이미지]
        all_imgs = re.findall(r'<img[^>]+src="([^">]+)"', content)
        target_imgs = all_imgs[:5]
        print(f"🖼️ 발견된 이미지: {len(all_imgs)}개 (최대 5개 처리 예정)")
        
        link = item.find('link').text
    except Exception as e:
        print(f"❌ RSS 추출 실패: {e}")
        return

    print("\n📸 [단계 3/5] 이미지 로드 및 변환 시작 (attachments)...")
    attachments = []
    for i, img_url in enumerate(target_imgs):
        try:
            print(f"   [{i+1}/{len(target_imgs)}] 이미지 다운로드 중: {img_url[:50]}...")
            img_res = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if img_res.status_code == 200:
                img_base64 = base64.b64encode(img_res.content).decode('utf-8')
                attachments.append({
                    "filename": f"attach_{i+1}_{datetime.now().strftime('%H%M%S')}.jpg",
                    "file_data": img_base64
                })
                print(f"   ✅ {i+1}번 이미지 변환 완료 (크기: {len(img_base64)} bytes)")
            else:
                print(f"   ⚠️ {i+1}번 이미지 다운로드 실패 (상태 코드: {img_res.status_code})")
        except Exception as e:
            print(f"   ❌ {i+1}번 이미지 처리 오류: {e}")

    print(f"\n🚀 [단계 4/5] 카페24 전송 페이로드 구성...")
    board_no = 8
    writer_name = "pp1125"
    print(f"   - 게시판 번호: {board_no}")
    print(f"   - 작성자명: {writer_name}")
    print(f"   - 첨부 파일 수: {len(attachments)}개")
    
    # 중복 방지를 위해 제목에 초단위 시간 추가
    unique_title = f"{title} ({datetime.now().strftime('%H:%M:%S')})"
    
    payload = {
        "shop_no": 1,
        "request": {
            "title": unique_title,
            "content": content + f'<br><br><a href="{link}">원문보기</a>',
            "writer_name": writer_name,
            "password": "Wkmg12345678!",
            "is_notice": "F",
            "is_secret": "F",
            "is_display": "T",  # 매뉴얼 기반: 노출 여부 명시
            "attachments": attachments,
            "file_count": len(attachments)
        }
    }

    print("\n📤 [단계 5/5] 최종 데이터 전송...")
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"📊 전송 결과 코드: {response.status_code}")
        if response.status_code == 201:
            print(f"🎉 [성공] 게시글이 정상적으로 등록되었습니다!")
        else:
            print(f"❌ [실패] 상세 메시지: {response.text}")
    except Exception as e:
        print(f"❌ 전송 중 시스템 오류 발생: {e}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        write_post_trace(token)
    else:
        sys.exit(1)
