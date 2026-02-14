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

# ✅ 기존 이미지 품질 설정 유지
MIN_BYTES_ACCEPT = 80_000
MIN_BYTES_KEEP = 25_000
MAX_IMAGES = 30
# ✅ 폰트 설정 상향
BASE_FONT_SIZE = 19 

# ============================================================================
# 🔐 1. 토큰 갱신 및 저장 (기존 로직 유지)
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
        except: pass
    return token_data.get("access_token")

# ============================================================================
# 🖼️ 2. 이미지 처리 유틸리티 (사용자 원본 로직 유지)
# ============================================================================
def set_type_param(url, type_value):
    try:
        p = urlparse(url)
        q = dict(parse_qsl(p.query, keep_blank_values=True))
        q["type"] = type_value
        return urlunparse(p._replace(query=urlencode(q, doseq=True)))
    except: return url

def download_best_image_by_size(base_url, referer):
    if not base_url: return None, 0
    candidates = [base_url, set_type_param(base_url, "w2000"), set_type_param(base_url, "w1200")]
    best_b, best_sz = None, 0
    for u in candidates:
        try:
            r = requests.get(u, headers={"User-Agent": USER_AGENT, "Referer": referer}, timeout=20)
            if r.status_code == 200 and len(r.content) > best_sz:
                best_b, best_sz = r.content, len(r.content)
            if best_sz >= MIN_BYTES_ACCEPT: break
        except: continue
    return best_b, best_sz

def upload_image_to_cafe24(access_token, b64_data):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"}
    payload = {"requests": [{"image": b64_data}]}
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    if res.status_code in [200, 201]:
        return res.json()["images"][0].get("url")
    return None

# ============================================================================
# 📄 3. 본문 추출 및 조립 (배치/서식 준수)
# ============================================================================
def process_content(access_token, real_url):
    res = requests.get(real_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    soup = BeautifulSoup(res.text, "html.parser")
    content_area = soup.select_one(".se-main-container") or soup.select_one("#post-view")
    
    html_parts = [f'<div style="font-size:{BASE_FONT_SIZE}px; line-height:1.8; color:#333; word-break:keep-all;">']
    first_img = None
    seen = set()

    # 모든 컴포넌트를 순차적으로 탐색하여 배치 순서 보존
    for comp in content_area.find_all(recursive=True):
        if comp in seen: continue

        # 이미지 처리
        if 'se-image' in comp.get('class', []):
            img_tag = comp.find('img')
            src = img_tag.get('data-src') or img_tag.get('src') if img_tag else None
            if src:
                best_b, best_sz = download_best_image_by_size(src, real_url)
                if best_b and best_sz > MIN_BYTES_KEEP:
                    up_url = upload_image_to_cafe24(access_token, base64.b64encode(best_b).decode())
                    if up_url:
                        if not first_img: first_img = up_url
                        html_parts.append(f'<div style="margin:30px 0; text-align:center;"><img src="{up_url}" style="max-width:100%; border-radius:10px;"></div>')
            for child in comp.find_all(): seen.add(child)
            seen.add(comp)

        # 텍스트 처리 (인라인 스타일 보존)
        elif 'se-text-paragraph' in comp.get('class', []):
            raw_html = str(comp)
            # 클래스 제거하고 폰트 크기만 상속받도록 조정 (컬러는 유지)
            clean_html = re.sub(r'class="[^"]*"', '', raw_html)
            clean_html = re.sub(r'font-size:[^;"]*;?', '', clean_html)
            html_parts.append(f'<div style="margin-bottom:15px;">{clean_html}</div>')
            seen.add(comp)

    html_parts.append("</div>")
    return "\n".join(html_parts), first_img

# ============================================================================
# 📤 4. 메인 실행
# ============================================================================
def main():
    access_token = refresh_and_save_token()
    
    # RSS에서 제목/링크 가져오기
    rss_res = requests.get(RSS_URL, timeout=10)
    item = ET.fromstring(rss_res.content).find(".//item")
    title = item.find("title").text.strip()
    log_no = item.find("link").text.split("/")[-1].split("?")[0]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"

    # 본문 및 이미지 처리
    content_html, thumb_url = process_content(access_token, real_url)

    # 게시글 생성
    payload = {
        "requests": [{
            "shop_no": 1, "writer": "관리자", "member_id": MALL_ID,
            "title": title, "content": content_html, "client_ip": "127.0.0.1"
        }]
    }
    if thumb_url:
        payload["requests"][0]["attach_file_urls"] = [{"name": "thumb.jpg", "url": thumb_url}]

    res = requests.post(f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles", 
                        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"},
                        json=payload, timeout=30)

    if res.status_code == 201:
        print(f"🎉 성공: {title}")

if __name__ == "__main__":
    main()
