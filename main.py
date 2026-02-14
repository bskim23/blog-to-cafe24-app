import os
import sys
import re
import base64
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from github import Github, Auth

# [환경설정]
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

def refresh_and_save_token():
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    res = requests.post(url, headers={"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"},
                        data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}, timeout=15)
    res.raise_for_status()
    data = res.json()
    if PA_TOKEN and GITHUB_REPO:
        try:
            Github(auth=Auth.Token(PA_TOKEN)).get_repo(GITHUB_REPO).create_secret("CAFE24_REFRESH_TOKEN", data.get("refresh_token"))
        except: pass
    return data.get("access_token")

def get_cafe24_latest_title(access_token):
    """카페24 해당 게시판의 가장 최신 글 제목 하나를 가져옴"""
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles?limit=1"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            articles = res.json().get("articles", [])
            if articles:
                return articles[0].get("title", "").strip()
    except Exception as e:
        print(f"⚠️ 카페24 최신글 조회 실패: {e}")
    return None

def download_and_upload(access_token, src, referer):
    try:
        clean_src = src.split('?')[0] + "?type=w2000" if 'pstatic.net' in src else src
        img_res = requests.get(clean_src, headers={"User-Agent": USER_AGENT, "Referer": referer}, timeout=20)
        if img_res.status_code == 200 and len(img_res.content) > MIN_BYTES_KEEP:
            b64 = base64.b64encode(img_res.content).decode()
            up_url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"}
            payload = {"requests": [{"image": b64}]}
            up_res = requests.post(up_url, headers=headers, json=payload, timeout=30)
            if up_res.status_code in [200, 201]:
                img_data = up_res.json()["images"][0]
                return img_data.get("url") or img_data.get("path")
    except: return None
    return None

def main():
    print("🚀 [START] 중복 체크 및 업로드 프로세스 시작")
    access_token = refresh_and_save_token()
    
    # 1. RSS 최신글 정보 가져오기
    rss_res = requests.get(RSS_URL, timeout=10)
    item = ET.fromstring(rss_res.content).find(".//item")
    if not item:
        print("❌ RSS 데이터를 가져올 수 없습니다."); return
    
    rss_title = item.find("title").text.strip()
    print(f"📡 RSS 최신글 제목: {rss_title}")

    # 2. 카페24 최신글 제목과 비교 (중복 체크 핵심)
    cafe24_title = get_cafe24_latest_title(access_token)
    print(f"🏪 카페24 최신글 제목: {cafe24_title}")

    if rss_title == cafe24_title:
        print("✅ 이미 최신글이 업로드되어 있습니다. 작업을 종료합니다.")
        return
    else:
        print("🆕 새 게시글 발견! 복사 작업을 시작합니다.")

    # 3. 본문 복사 및 이미지 처리 진행
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={item.find('link').text.split('/')[-1].split('?')[0]}"
    soup = BeautifulSoup(requests.get(real_url, headers={"User-Agent": USER_AGENT}).text, "html.parser")
    content_area = soup.select_one(".se-main-container")
    
    html_parts = [f'<div style="font-size:{BASE_FONT_SIZE}px; line-height:1.8; color:#333; word-break:keep-all;">']
    first_valid_image = None
    seen = set()

    for el in content_area.find_all(recursive=True):
        if el in seen: continue
        img_tag = el.find('img') if el.name != 'img' else el
        if img_tag and (el.get('class') and any('se-image' in c for c in el.get('class')) or el.name == 'img'):
            src = img_tag.get('data-src') or img_tag.get('src')
            if src and not src.endswith('.svg'):
                uploaded_path = download_and_upload(access_token, src, real_url)
                if uploaded_path:
                    if not first_valid_image: first_valid_image = uploaded_path
                    html_parts.append(f'<div style="margin:35px 0; text-align:center;"><img src="{uploaded_path}" style="max-width:100%; height:auto; border-radius:12px;"></div>')
            for c in el.find_all(): seen.add(c)
            seen.add(el)
        elif el.get('class') and 'se-text-paragraph' in el.get('class'):
            inner_html = re.sub(r'class="[^"]*"', '', str(el))
            inner_html = re.sub(r'font-size:[^;"]*;?', '', inner_html)
            html_parts.append(f'<div style="margin-bottom:18px;">{inner_html}</div>')
            seen.add(el)

    html_parts.append("</div>")
    
    # 4. 카페24 업로드
    article_data = {
        "requests": [{
            "shop_no": 1, "writer": "관리자", "member_id": MALL_ID,
            "title": rss_title, "content": "\n".join(html_parts), "client_ip": "127.0.0.1"
        }]
    }
    if first_valid_image:
        article_data["requests"][0]["attach_file_urls"] = [{"name": "thumb.jpg", "url": first_valid_image}]

    res = requests.post(f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles",
                        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"},
                        json=article_data, timeout=30)
    
    if res.status_code == 201:
        print(f"🎉 새 게시글 업로드 성공: {rss_title}")

if __name__ == "__main__":
    main()
