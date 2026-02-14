import os
import sys
import re
import json
import base64
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, Tag
from github import Github, Auth
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# ============================================================================
# 설정
# ============================================================================
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')
PA_TOKEN = os.environ.get('PA_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY')

BOARD_NO = 8
RSS_URL = "https://rss.blog.naver.com/mediheally_lab.xml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ✅ 품질 설정
MIN_BYTES_KEEP = 25_000
MAX_IMAGES = 30
# ✅ 폰트 설정 (기존보다 더 크게 상향)
BASE_FONT_SIZE = 19 
LINE_HEIGHT = "1.8"

# ============================================================================
# 🔐 토큰 갱신 (최우선 처리)
# ============================================================================
def refresh_and_save_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}

    res = requests.post(url, headers=headers, data=data, timeout=10)
    res.raise_for_status()
    token_data = res.json()
    new_refresh_token = token_data.get("refresh_token")

    if PA_TOKEN and GITHUB_REPO:
        try:
            g = Github(auth=Auth.Token(PA_TOKEN))
            repo = g.get_repo(GITHUB_REPO)
            repo.create_secret("CAFE24_REFRESH_TOKEN", new_refresh_token)
            print(f"✅ 새 리프레시 토큰 로그: {new_refresh_token}")
        except Exception as e:
            print(f"⚠️ GitHub 저장 실패: {e}")

    return token_data.get("access_token")

# ============================================================================
# 📄 네이버 RSS 및 본문 추출 (순서/서식 보존)
# ============================================================================
def fetch_latest_post():
    rss_res = requests.get(RSS_URL, timeout=10)
    rss_root = ET.fromstring(rss_res.content)
    item = rss_root.find(".//item")
    post_title = item.find("title").text.strip()
    post_link = item.find("link").text.strip()
    log_no = post_link.split("/")[-1].split("?")[0]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
    return post_title, real_url

def extract_content_with_style(real_url):
    res = requests.get(real_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    soup = BeautifulSoup(res.text, "html.parser")
    content_area = soup.select_one(".se-main-container")
    
    blocks = []
    # 네이버 스마트에디터의 주요 컴포넌트들을 순서대로 탐색
    components = content_area.find_all(recursive=True)
    
    seen_elements = set()

    for comp in components:
        if comp in seen_elements: continue
        
        # 1. 이미지 처리
        if 'se-image' in comp.get('class', []):
            img_tag = comp.find('img')
            if img_tag:
                src = img_tag.get('data-src') or img_tag.get('src')
                blocks.append({"type": "image", "src": src})
                for child in comp.find_all(): seen_elements.add(child)
                seen_elements.add(comp)
        
        # 2. 텍스트 처리 (문단 단위)
        elif 'se-text-paragraph' in comp.get('class', []):
            # 인라인 스타일(컬러, 굵기)이 포함된 HTML 추출
            # 폰트 사이즈는 카페24 기준에 맞춰 강제 조정하기 위해 정규식 준비
            raw_html = str(comp)
            # 가독성을 위해 불필요한 클래스 제거 및 정리
            clean_html = re.sub(r'class="[^"]*"', '', raw_html)
            blocks.append({"type": "text", "html": clean_html})
            seen_elements.add(comp)
            
    return blocks

# ============================================================================
# 📤 카페24 업로드 로직
# ============================================================================
def upload_images_and_build_html(access_token, blocks, real_url):
    html_parts = [f'<div style="font-size:{BASE_FONT_SIZE}px; line-height:{LINE_HEIGHT}; color:#333; word-break:keep-all;">']
    first_img = None

    for b in blocks:
        if b["type"] == "image":
            # 이미지 다운로드 및 업로드 (기존 download_best_image_by_size 로직 활용 가정)
            # 여기서는 지면상 핵심 업로드 부분만 표현
            img_res = download_image_to_base64(b["src"], real_url)
            if img_res:
                path = upload_to_cafe24_api(access_token, img_res)
                if path:
                    if not first_img: first_img = path
                    html_parts.append(f'<div style="margin:30px 0; text-align:center;"><img src="{path}" style="max-width:100%;"></div>')
        
        elif b["type"] == "text":
            # 원본 텍스트의 컬러/음영을 살리되 폰트 크기만 BASE_FONT_SIZE로 보정
            text_html = b["html"]
            # 네이버의 미세 폰트 사이즈를 무시하고 일괄 크게 만듦 (원본 컬러는 유지)
            text_html = re.sub(r'style="[^"]*font-size:[^;"]*;?"', '', text_html) 
            html_parts.append(f'<div style="margin-bottom:15px;">{text_html}</div>')

    html_parts.append("</div>")
    return "\n".join(html_parts), first_img

# (이하 download_image_to_base64, upload_to_cafe24_api, create_board_article 등 기존 유틸 함수 유지)
# ============================================================================

def main():
    print("🚀 카페24 자동 업로드 프로세스 시작")
    access_token = refresh_and_save_token()
    title, real_url = fetch_latest_post()
    
    print(f"📦 원본 분석 중: {title}")
    blocks = extract_content_with_style(real_url)
    
    content_html, thumb_url = upload_images_and_build_html(access_token, blocks, real_url)
    
    res = create_board_article(access_token, title, content_html, thumb_url)
    if res.status_code == 201:
        print("🎉 업로드 완료!")

if __name__ == "__main__":
    main()
