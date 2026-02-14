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

# ✅ 품질 및 스타일 설정
MIN_BYTES_KEEP = 25_000
MAX_IMAGES = 30
BASE_FONT_SIZE = 19  # 요청하신 대로 크게 설정
LINE_HEIGHT = "1.8"

# ============================================================================
# 🔐 1. 토큰 갱신 및 저장
# ============================================================================
def refresh_and_save_token():
    print("🔐 [1/5] 토큰 갱신 시작", flush=True)
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()

    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}

    res = requests.post(url, headers=headers, data=data, timeout=15)
    res.raise_for_status()
    token_data = res.json()
    
    access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token")

    print(f"✅ 새 리프레시 토큰 로그: {new_refresh_token}")

    if PA_TOKEN and GITHUB_REPO:
        try:
            auth = Auth.Token(PA_TOKEN)
            g = Github(auth=auth)
            repo = g.get_repo(GITHUB_REPO)
            repo.create_secret("CAFE24_REFRESH_TOKEN", new_refresh_token)
            print("✅ GitHub Secrets 업데이트 완료")
        except Exception as e:
            print(f"⚠️ GitHub Secrets 업데이트 실패: {e}")

    return access_token

# ============================================================================
# 📄 2. 네이버 데이터 추출 (순서/서식 보존)
# ============================================================================
def fetch_latest_post():
    print("📡 [2/5] RSS 최신글 확인", flush=True)
    rss_res = requests.get(RSS_URL, timeout=10)
    rss_root = ET.fromstring(rss_res.content)
    item = rss_root.find(".//item")
    if not item:
        print("❌ RSS 게시글 없음"); sys.exit(1)

    post_title = (item.find("title").text or "").strip()
    post_link = (item.find("link").text or "").strip()
    log_no = post_link.split("/")[-1].split("?")[0]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
    return post_title, real_url

def extract_content_with_style(real_url):
    print("🧱 [3/5] 본문 서식 분석 시작", flush=True)
    res = requests.get(real_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    soup = BeautifulSoup(res.text, "html.parser")
    content_area = soup.select_one(".se-main-container") or soup.select_one("#post-view")
    
    blocks = []
    # 모든 직계 자식 요소를 순서대로 탐색하여 배치 순서 보존
    components = content_area.find_all(recursive=True)
    seen_elements = set()

    for comp in components:
        if comp in seen_elements: continue
        
        # 이미지 컴포넌트
        if 'se-image' in comp.get('class', []):
            img_tag = comp.find('img')
            if img_tag:
                src = img_tag.get('data-src') or img_tag.get('src')
                if src:
                    blocks.append({"type": "image", "src": src})
                # 하위 요소 중복 방지
                for child in comp.find_all(): seen_elements.add(child)
                seen_elements.add(comp)
        
        # 텍스트 컴포넌트
        elif 'se-text-paragraph' in comp.get('class', []):
            # 태그 내 인라인 스타일(색상 등) 포함하여 추출
            # 가독성을 위해 불필요한 클래스만 제거
            raw_html = str(comp)
            clean_html = re.sub(r'class="[^"]*"', '', raw_html)
            blocks.append({"type": "text", "html": clean_html})
            seen_elements.add(comp)
            
    return blocks

# ============================================================================
# 🖼️ 3. 이미지 처리 유틸리티 (기존 로직 보강)
# ============================================================================
def download_image_to_base64(url, referer):
    headers = {"User-Agent": USER_AGENT, "Referer": referer}
    try:
        # 고화질 시도를 위해 w2000 파라미터 강제 적용 시도
        if 'pstatic.net' in url:
            url = url.split('?')[0] + "?type=w2000"
        
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200 and len(r.content) > MIN_BYTES_KEEP:
            return base64.b64encode(r.content).decode()
    except:
        return None
    return None

def upload_image_to_cafe24(access_token, b64_data):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    payload = {"requests": [{"image": b64_data}]}
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    if res.status_code in [200, 201]:
        data = res.json()
        return data["images"][0].get("url")
    return None

# ============================================================================
# 📤 4. 최종 조립 및 업로드
# ============================================================================
def upload_to_cafe24(access_token, title, blocks, real_url):
    print("📤 [4/5] 카페24 데이터 조립 및 이미지 업로드", flush=True)
    html_parts = [f'<div style="font-size:{BASE_FONT_SIZE}px; line-height:{LINE_HEIGHT}; color:#333; word-break:keep-all;">']
    first_img_url = None
    img_count = 0

    for b in blocks:
        if b["type"] == "image" and img_count < MAX_IMAGES:
            b64 = download_image_to_base64(b["src"], real_url)
            if b64:
                uploaded_url = upload_image_to_cafe24(access_token, b64)
                if uploaded_url:
                    if not first_img_url: first_img_url = uploaded_url
                    html_parts.append(f'<div style="margin:30px 0; text-align:center;"><img src="{uploaded_url}" style="max-width:100%; height:auto; border-radius:10px;"></div>')
                    img_count += 1
        
        elif b["type"] == "text":
            # 원본의 컬러 서식은 살리고, 폰트 사이즈만 강제로 크게 조정
            text_html = b["html"]
            # 네이버의 고정된 작은 폰트 스타일 제거 (BASE_FONT_SIZE 상속 유도)
            text_html = re.sub(r'font-size:[^;"]*;?', '', text_html)
            html_parts.append(f'<div style="margin-bottom:12px;">{text_html}</div>')

    html_parts.append("</div>")
    content_html = "\n".join(html_parts)

    print("📤 [5/5] 게시글 생성", flush=True)
    api_url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    req_body = {
        "shop_no": 1,
        "writer": "관리자",
        "member_id": MALL_ID,
        "title": title,
        "content": content_html,
        "client_ip": "127.0.0.1"
    }
    if first_img_url:
        req_body["attach_file_urls"] = [{"name": "thumb.jpg", "url": first_img_url}]

    res = requests.post(api_url, headers=headers, json={"requests": [req_body]}, timeout=30)
    return res

# ============================================================================
# 실행
# ============================================================================
def main():
    try:
        access_token = refresh_and_save_token()
        title, real_url = fetch_latest_post()
        blocks = extract_content_with_style(real_url)
        res = upload_to_cafe24(access_token, title, blocks, real_url)
        
        if res.status_code == 201:
            print(f"\n🎉 모든 작업 완료! 제목: {title}")
        else:
            print(f"❌ 실패: {res.status_code} {res.text}")
    except Exception as e:
        print(f"❌ 치명적 에러: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
