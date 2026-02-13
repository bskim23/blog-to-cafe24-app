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

def get_access_token():
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
    try:
        response = requests.get(rss_url, timeout=10)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)
        item = root.find('.//item')
        if item is None: return None
        
        title = item.find('title').text
        link = item.find('link').text
        desc = item.find('description').text
        img = re.findall(r'<img[^>]+src="([^">]+)"', desc)
        
        return {"title": title, "link": link, "content": desc, "img": img[0] if img else None}
    except:
        return None

def upload_image_to_cafe24(access_token, image_url):
    if not image_url: return None
    try:
        img_res = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        img_data = base64.b64encode(img_res.content).decode('utf-8')
        url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/images"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {"requests": [{"image_data": img_data, "filename": f"img_{datetime.now().strftime('%H%M%S')}.jpg"}]}
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['images'][0]['url'] if res.status_code == 201 else None
    except:
        return None

def write_post(access_token, post_data, cafe_img_url):
    board_no = 8
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    # 본문 구성 (이미지가 없을 경우 대비)
    img_tag = f'<img src="{cafe_img_url}" style="max-width:100%;"><br>' if cafe_img_url else ""
    content_html = f'<div style="text-align:center;">{img_tag}<div style="text-align:left;">{post_data["content"]}</div></div>'
    
    # [422 해결용 정제된 페이로드]
    payload = {
        "shop_no": 1,
        "request": {
            "title": post_data['title'],
            "content": content_html,
            "writer": "관리자",
            "author_password": "password123!",
            "is_notice": "F",
            "is_secret": "F"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print(f"🎉 성공: {post_data['title']}")
    else:
        print(f"❌ 실패 코드 {response.status_code}: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        post = get_latest_rss("https://rss.blog.naver.com/mediheally_lab.xml")
        if post:
            cafe_img = upload_image_to_cafe24(token, post['img'])
            write_post(token, post, cafe_img)
    else:
        sys.exit(1)
