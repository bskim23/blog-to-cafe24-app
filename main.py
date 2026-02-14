import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from github import Github

# ==============================================================================
# 설정
# ==============================================================================
MALL_ID = os.environ.get('CAFE24_MALL_ID')
CLIENT_ID = os.environ.get('CAFE24_CLIENT_ID')
CLIENT_SECRET = os.environ.get('CAFE24_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('CAFE24_REFRESH_TOKEN')
PA_TOKEN = os.environ.get('PA_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY')

BOARD_NO = 8
PASSWORD = "1234"
RSS_URL = "https://rss.blog.naver.com/mediheally_lab.xml"

# ==============================================================================
# 1. Refresh Token 갱신 및 GitHub Secrets 업데이트
# ==============================================================================
def refresh_access_token():
    """
    Access Token 발급 및 새로운 Refresh Token으로 GitHub Secrets 자동 업데이트
    """
    print("🔄 [1/4] Access Token 발급 중...")
    
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    try:
        res = requests.post(url, headers=headers, data=data)
        res.raise_for_status()
        token_data = res.json()
        
        access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')
        
        if not access_token or not new_refresh_token:
            print("❌ 토큰 발급 실패: 응답에 토큰이 없습니다.")
            sys.exit(1)
        
        # GitHub Secrets 업데이트
        if PA_TOKEN and GITHUB_REPO:
            try:
                g = Github(PA_TOKEN)
                repo = g.get_repo(GITHUB_REPO)
                
                # Refresh Token 업데이트
                repo.create_secret("CAFE24_REFRESH_TOKEN", new_refresh_token)
                print(f"✅ GitHub Secrets 업데이트 완료")
                print(f"   새 Refresh Token: {new_refresh_token[:20]}...")
                
            except Exception as e:
                print(f"⚠️  GitHub Secrets 업데이트 실패: {e}")
                print(f"   수동으로 업데이트하세요: {new_refresh_token}")
        
        return access_token
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 토큰 발급 실패: {e}")
        sys.exit(1)

# ==============================================================================
# 2. 네이버 블로그 크롤링
# ==============================================================================
def fetch_latest_post():
    """
    네이버 블로그 RSS에서 최신 글 가져오기
    """
    print("\n📡 [2/4] 네이버 블로그 최신 글 크롤링 중...")
    
    try:
        # RSS 파싱
        rss_res = requests.get(RSS_URL, timeout=10)
        rss_res.raise_for_status()
        rss_root = ET.fromstring(rss_res.text)
        
        item = rss_root.find('.//item')
        if not item:
            print("❌ RSS에 게시글이 없습니다.")
            sys.exit(1)
        
        post_title = item.find('title').text
        post_link = item.find('link').text
        
        print(f"   제목: {post_title}")
        print(f"   링크: {post_link}")
        
        # iframe 주소를 실제 주소로 변환
        log_no = post_link.split('/')[-1]
        real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
        
        return post_title, post_link, real_url
        
    except Exception as e:
        print(f"❌ RSS 파싱 실패: {e}")
        sys.exit(1)

# ==============================================================================
# 3. 본문 및 이미지 추출
# ==============================================================================
def extract_content_and_images(real_url):
    """
    네이버 블로그 본문 및 이미지 추출 (최대 5개)
    """
    print("\n🖼️  [3/4] 본문 및 이미지 추출 중...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        res = requests.get(real_url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 본문 영역 찾기
        content_area = soup.select_one('.se-main-container') or soup.select_one('#post-view')
        
        if not content_area:
            print("❌ 본문 추출 실패: 네이버 블로그 구조를 찾을 수 없습니다.")
            sys.exit(1)
        
        # 이미지 추출 (최대 5개)
        attachments = []
        img_tags = content_area.find_all('img')
        
        for idx, img in enumerate(img_tags):
            if idx >= 5:  # 최대 5개
                break
            
            src = img.get('src') or img.get('data-lazy-src') or img.get('data-src')
            
            if src and 'postfiles.pstatic.net' in src:
                try:
                    img_res = requests.get(src, headers=headers, timeout=10)
                    img_res.raise_for_status()
                    
                    # Base64 인코딩
                    b64_img = base64.b64encode(img_res.content).decode()
                    
                    attachments.append({
                        "filename": f"image_{idx+1}.jpg",
                        "file_data": b64_img
                    })
                    
                    print(f"   ✓ 이미지 {idx+1} 다운로드 완료 ({len(img_res.content)} bytes)")
                    
                except Exception as e:
                    print(f"   ⚠️  이미지 {idx+1} 다운로드 실패: {e}")
        
        # 본문 텍스트
        text_content = content_area.get_text(separator='\n', strip=True)
        
        print(f"   총 {len(attachments)}개 이미지 추출 완료")
        
        return text_content, attachments
        
    except Exception as e:
        print(f"❌ 콘텐츠 추출 실패: {e}")
        sys.exit(1)

# ==============================================================================
# 4. 카페24 업로드
# ==============================================================================
def upload_to_cafe24(access_token, title, content, original_link, attachments):
    """
    카페24 갤러리 게시판에 업로드
    """
    print("\n📤 [4/4] 카페24 갤러리 게시판 업로드 중...")
    
    # 이미지 없으면 업로드 불가
    if not attachments:
        print("❌ 갤러리 게시판은 최소 1개의 이미지가 필요합니다.")
        sys.exit(1)
    
    # 본문 구성 (원문 링크 추가)
    final_content = f"{content}\n\n<br><br><a href='{original_link}' target='_blank'>📝 원문 보러가기</a>"
    
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": BOARD_NO,
            "title": title,
            "content": final_content,
            "writer": "관리자",
            "password": PASSWORD,
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments
        }
    }
    
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if res.status_code == 201:
            print("\n🎉 ════════════════════════════════════════")
            print("   ✅ 게시글 업로드 성공!")
            print(f"   📝 제목: {title}")
            print(f"   🖼️  이미지: {len(attachments)}개")
            print(f"   🔗 확인: https://{MALL_ID}.cafe24.com")
            print("════════════════════════════════════════\n")
        else:
            print(f"❌ 업로드 실패 ({res.status_code})")
            print(f"   응답: {res.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 업로드 요청 실패: {e}")
        sys.exit(1)

# ==============================================================================
# 메인 실행
# ==============================================================================
def main():
    print("\n🚀 ════════════════════════════════════════")
    print("   네이버 → 카페24 자동 포스팅 시작")
    print("════════════════════════════════════════\n")
    
    # 환경 변수 체크
    required_vars = [MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]
    if not all(required_vars):
        print("❌ 환경 변수가 설정되지 않았습니다.")
        print("   GitHub Secrets를 확인하세요.")
        sys.exit(1)
    
    # 1. 토큰 갱신
    access_token = refresh_access_token()
    
    # 2. 최신 글 가져오기
    title, original_link, real_url = fetch_latest_post()
    
    # 3. 본문 및 이미지 추출
    content, attachments = extract_content_and_images(real_url)
    
    # 4. 카페24 업로드
    upload_to_cafe24(access_token, title, content, original_link, attachments)
    
    print("✅ 모든 작업 완료!\n")

if __name__ == "__main__":
    main()
