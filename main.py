import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# 1. 환경변수 설정
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')

def get_access_token():
    """토큰 갱신 및 저장 대기 (무한 동력)"""
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        new_refresh = result.get('refresh_token')
        if new_refresh:
            env_file = os.getenv('GITHUB_ENV')
            if env_file:
                with open(env_file, "a") as f:
                    f.write(f"NEW_REFRESH_TOKEN={new_refresh}\n")
        return result.get('access_token')
    except:
        return None

def get_latest_rss(rss_url):
    """네이버 RSS에서 최신 글 추출"""
    response = requests.get(rss_url)
    response.encoding = 'utf-8'
    root = ET.fromstring(response.text)
    item = root.find('.//item')
    if item is None: return None

    title = item.find('title').text
    link = item.find('link').text
    description = item.find('description').text
    img_urls = re.findall(r'<img[^>]+src="([^">]+)"', description)
    return {"title": title, "link": link, "content": description, "img": img_urls[0] if img_urls else None}

def upload_image_to_cafe24(access_token, image_url):
    """이미지 업로드 (갤러리 썸네일용)"""
    if not image_url: return None
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        img_data = base64.b64encode(img_res.content).decode('utf-8')
        url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/images"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {"requests": [{"image_data": img_data, "filename": "thumb.jpg"}]}
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['images'][0]['url'] if res.status_code == 201 else None
    except:
        return None

def write_post(access_token, post_data, cafe_img_url):
    """최종 게시글 작성 (갤러리 규격 준수)"""
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "X-Cafe24-Api-Version": "2025-12-01"}
    
    display_img = cafe_img_url if cafe_img_url else "https://sample.cafe24.com/sample_image.jpg"
    content_html = f'<div style="text-align:center;"><img src="{display_img}" style="max-width:100%;"><br><br><div style="text-align:left;">{post_data["content"]}<br><br><a href="{post_data["link"]}" target="_blank">👉 원문 보기</a></div></div>'
    
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": board_no,
            "title": post_data['title'],
            "content": content_html,
            "writer": "관리자",
            "author_password": "wkmg_pass_1234",
            "is_notice": "F", "is_secret": "F", "article_type": "A", "use_image_hosting": "T"
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 201: print(f"🎉 성공: {post_data['title']}")
    else: print(f"❌ 실패: {res.text}")

if __name__ == "__main__":
    RSS_URL = "https://rss.blog.naver.com/pp1125.xml"
    token = get_access_token()
    if token:
        post = get_latest_rss(RSS_URL)
        if post:
            cafe_img = upload_image_to_cafe24(token, post['img'])
            write_post(token, post, cafe_img)
    else:
        sys.exit(1)
