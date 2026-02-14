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

# ✅ 방지책: 25KB 미만(스티커, 아이콘)은 목록/본문에서 제외
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

def download_and_upload(access_token, src, referer):
    """원본 고화질 이미지를 다운로드하여 카페24 서버에 업로드"""
    try:
        # 1. 원본 파라미터 강제 (w2000)
        clean_src = src.split('?')[0] + "?type=w2000" if 'pstatic.net' in src else src
        img_res = requests.get(clean_src, headers={"User-Agent": USER_AGENT, "Referer": referer}, timeout=20)
        
        # 2. 용량 스크리닝 (아이콘/썸네일용 작은 이미지 필터링)
        if img_res.status_code == 200 and len(img_res.content) > MIN_BYTES_KEEP:
            b64 = base64.b64encode(img_res.content).decode()
            up_url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"}
            payload = {"requests": [{"image": b64}]}
            up_res = requests.post(up_url, headers=headers, json=payload, timeout=30)
            
            if up_res.status_code in [200, 201]:
                # 3. 카페24 내부 절대 경로 반환
                img_data = up_res.json()["images"][0]
                return img_data.get("url") or img_data.get("path")
    except: return None
    return None

def main():
    print("🚀 [PROCESS] 목록 썸네일 원본 유지 모드 가동")
    access_token = refresh_and_save_token()
    
    # 네이버 최신글 정보
    rss_res = requests.get(RSS_URL, timeout=10)
    item = ET.fromstring(rss_res.content).find(".//item")
    title = item.find("title").text.strip()
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={item.find('link').text.split('/')[-1].split('?')[0]}"

    soup = BeautifulSoup(requests.get(real_url, headers={"User-Agent": USER_AGENT}).text, "html.parser")
    content_area = soup.select_one(".se-main-container")
    
    html_parts = [f'<div style="font-size:{BASE_FONT_SIZE}px; line-height:1.8; color:#333; word-break:keep-all;">']
    first_valid_image = None # 목록 썸네일로 사용할 '원본' 경로 저장
    seen = set()

    for el in content_area.find_all(recursive=True):
        if el in seen: continue

        # 이미지 발견 및 처리
        img_tag = el.find('img') if el.name != 'img' else el
        if img_tag and (el.get('class') and any('se-image' in c for c in el.get('class')) or el.name == 'img'):
            src = img_tag.get('data-src') or img_tag.get('src')
            if src and not src.endswith('.svg'):
                # 원본 이미지를 카페24 서버로 옮기고 경로 획득
                uploaded_path = download_and_upload(access_token, src, real_url)
                if uploaded_path:
                    # ✅ 첫 번째로 성공한 원본 이미지를 목록 썸네일용으로 찜함
                    if not first_valid_image: first_valid_image = uploaded_path
                    html_parts.append(f'<div style="margin:35px 0; text-align:center;"><img src="{uploaded_path}" style="max-width:100%; height:auto; border-radius:12px;"></div>')
            for c in el.find_all(): seen.add(c)
            seen.add(el)

        # 텍스트 발견 및 처리 (서식 유지)
        elif el.get('class') and 'se-text-paragraph' in el.get('class'):
            inner_html = re.sub(r'class="[^"]*"', '', str(el))
            inner_html = re.sub(r'font-size:[^;"]*;?', '', inner_html)
            html_parts.append(f'<div style="margin-bottom:18px;">{inner_html}</div>')
            seen.add(el)

    html_parts.append("</div>")
    
    # 게시글 데이터 조립
    article_data = {
        "requests": [{
            "shop_no": 1, "writer": "관리자", "member_id": MALL_ID,
            "title": title, "content": "\n".join(html_parts), "client_ip": "127.0.0.1"
        }]
    }
    
    # ✅ 목록에서 '원본' 이미지가 보이도록 설정
    if first_valid_image:
        article_data["requests"][0]["attach_file_urls"] = [{"name": "original_thumb.jpg", "url": first_valid_image}]

    res = requests.post(f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles",
                        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"},
                        json=article_data, timeout=30)
    
    if res.status_code == 201:
        print(f"🎉 업로드 성공: {title}")
        if first_valid_image: print(f"🖼️ 목록 썸네일(원본 매칭): {first_valid_image}")

if __name__ == "__main__":
    main()
