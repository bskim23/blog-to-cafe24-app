import os
import sys
import re
import json
import base64
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from github import Github, Auth
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# ============================================================================
# 설정 (기본값 유지)
# ============================================================================
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')
PA_TOKEN = os.environ.get('PA_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY')

BOARD_NO = 8
RSS_URL = "https://rss.blog.naver.com/mediheally_lab.xml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

MIN_BYTES_KEEP = 25_000
BASE_FONT_SIZE = 19 

# ============================================================================
# 🔐 1. 토큰 갱신 및 저장
# ============================================================================
def refresh_and_save_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    res = requests.post(url, headers=headers, data=data, timeout=15)
    res.raise_for_status()
    token_data = res.json()
    new_refresh_token = token_data.get("refresh_token")
    if PA_TOKEN and GITHUB_REPO:
        try:
            g = Github(auth=Auth.Token(PA_TOKEN))
            repo = g.get_repo(GITHUB_REPO)
            repo.create_secret("CAFE24_REFRESH_TOKEN", new_refresh_token)
            print(f"✅ 새 리프레시 토큰 갱신 성공")
        except: pass
    return token_data.get("access_token")

# ============================================================================
# 🖼️ 2. 이미지 처리 (사용자 원본의 안정적인 로직)
# ============================================================================
def download_image_as_b64(url, referer):
    headers = {"User-Agent": USER_AGENT, "Referer": referer}
    try:
        # 고화질 파라미터 시도
        if 'pstatic.net' in url:
            url = url.split('?')[0] + "?type=w2000"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200 and len(r.content) > MIN_BYTES_KEEP:
            return base64.b64encode(r.content).decode()
    except: return None
    return None

def upload_to_cafe24_img(access_token, b64):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"}
    payload = {"requests": [{"image": b64}]}
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    if res.status_code in [200, 201]:
        return res.json()["images"][0].get("url")
    return None

# ============================================================================
# 📄 3. 본문 조립 (이미지 탐지 강화 + 배치 준수)
# ============================================================================
def build_final_content(access_token, real_url):
    res = requests.get(real_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    soup = BeautifulSoup(res.text, "html.parser")
    content_area = soup.select_one(".se-main-container")
    
    html_parts = [f'<div style="font-size:{BASE_FONT_SIZE}px; line-height:1.8; color:#333; word-break:keep-all;">']
    first_img_url = None
    seen = set()

    # 모든 자식 요소를 순회하며 이미지와 텍스트를 정확한 순서로 추출
    for el in content_area.find_all(recursive=True):
        if el in seen: continue

        # 1. 이미지 찾기 (클래스 기반 + 태그 기반 이중 체크)
        is_img_comp = 'se-image' in el.get('class', []) or el.name == 'img'
        if is_img_comp and el.name != 'div': # 실제 img 태그가 포함된 컨테이너인 경우
            img_tag = el if el.name == 'img' else el.find('img')
            if img_tag:
                src = img_tag.get('data-src') or img_tag.get('src')
                if src and not src.endswith('.svg'): # 아이콘 제외
                    b64 = download_image_as_b64(src, real_url)
                    if b64:
                        up_url = upload_to_cafe24_img(access_token, b64)
                        if up_url:
                            if not first_img_url: first_img_url = up_url
                            html_parts.append(f'<div style="margin:30px 0; text-align:center;"><img src="{up_url}" style="max-width:100%; height:auto; border-radius:10px;"></div>')
                # 처리한 요소와 그 자식들을 중복 방지 목록에 추가
                for child in el.find_all(): seen.add(child)
                seen.add(el)

        # 2. 텍스트 찾기
        elif 'se-text-paragraph' in el.get('class', []):
            raw_html = str(el)
            # 불필요한 클래스 제거 & 폰트 사이즈는 전역 설정(19px)을 따르도록 인라인 크기만 삭제
            clean_html = re.sub(r'class="[^"]*"', '', raw_html)
            clean_html = re.sub(r'font-size:[^;"]*;?', '', clean_html)
            html_parts.append(f'<div style="margin-bottom:15px;">{clean_html}</div>')
            seen.add(el)

    html_parts.append("</div>")
    return "\n".join(html_parts), first_img_url

# ============================================================================
# 📤 4. 메인 실행
# ============================================================================
def main():
    print("🚀 [START] 카페24 업로드 프로세스")
    access_token = refresh_and_save_token()
    
    # RSS 정보 호출
    rss_res = requests.get(RSS_URL, timeout=10)
    item = ET.fromstring(rss_res.content).find(".//item")
    title = item.find("title").text.strip()
    log_no = item.find("link").text.split("/")[-1].split("?")[0]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
    print(f"📝 대상 게시글: {title}")

    # 본문 조립 및 이미지 업로드
    final_html, thumb_url = build_final_content(access_token, real_url)

    # 게시글 업로드
    payload = {
        "requests": [{
            "shop_no": 1, "writer": "관리자", "member_id": MALL_ID,
            "title": title, "content": final_html, "client_ip": "127.0.0.1"
        }]
    }
    # 목록에서 이미지가 보이게 하는 핵심 설정
    if thumb_url:
        payload["requests"][0]["attach_file_urls"] = [{"name": "thumbnail.jpg", "url": thumb_url}]
        print(f"🖼️ 썸네일 등록 완료: {thumb_url}")

    res = requests.post(f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles", 
                        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"},
                        json=payload, timeout=30)

    if res.status_code == 201:
        print(f"🎉 성공: {title}")
    else:
        print(f"❌ 실패: {res.text}")

if __name__ == "__main__":
    main()
