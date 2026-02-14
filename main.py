import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from github import Github, Auth
import json

# ============================================================================
# 🔍 디버그: import 완료 확인
# ============================================================================
print("=" * 70, flush=True)
print("🔍 [DEBUG] 스크립트 시작 - 모든 라이브러리 import 성공", flush=True)
print("=" * 70, flush=True)
sys.stdout.flush()

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
PASSWORD = "1234"
WRITER_NAME = "메디힐리"
RSS_URL = "https://rss.blog.naver.com/mediheally_lab.xml"

# ============================================================================
# 🔍 디버그: 환경변수 확인
# ============================================================================
print("\n🔍 [DEBUG] 환경변수 로드 상태:", flush=True)
print(f"   MALL_ID          : {'✅ ' + MALL_ID if MALL_ID else '❌ None'}", flush=True)
print(f"   CLIENT_ID        : {'✅ ' + CLIENT_ID[:10] + '...' if CLIENT_ID else '❌ None'}", flush=True)
print(f"   CLIENT_SECRET    : {'✅ ' + CLIENT_SECRET[:10] + '...' if CLIENT_SECRET else '❌ None'}", flush=True)
print(f"   REFRESH_TOKEN    : {'✅ ' + REFRESH_TOKEN[:20] + '...' if REFRESH_TOKEN else '❌ None'}", flush=True)
print(f"   PA_TOKEN         : {'✅ 있음' if PA_TOKEN else '❌ None'}", flush=True)
print(f"   GITHUB_REPO      : {'✅ ' + GITHUB_REPO if GITHUB_REPO else '❌ None'}", flush=True)
print(f"   BOARD_NO         : {BOARD_NO}", flush=True)
print(f"   PASSWORD         : {PASSWORD}", flush=True)
print(f"   WRITER_NAME      : {WRITER_NAME}", flush=True)
print(f"   RSS_URL          : {RSS_URL}", flush=True)
print("=" * 70 + "\n", flush=True)
sys.stdout.flush()

# ============================================================================
# 🔐 [최우선] 토큰 갱신 및 즉시 저장
# ============================================================================
def refresh_and_save_token():
    """
    ⚠️ 최우선 작업: Access Token 발급 및 새 Refresh Token 즉시 저장
    """
    print("=" * 70, flush=True)
    print("🔐 [최우선] 토큰 갱신 및 저장 시작", flush=True)
    print("=" * 70, flush=True)
    sys.stdout.flush()
    
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    print(f"🔍 [DEBUG] API URL: {url}", flush=True)
    sys.stdout.flush()
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    try:
        print(f"\n🔍 [STEP 1] POST 요청 전송 중...", flush=True)
        sys.stdout.flush()
        
        res = requests.post(url, headers=headers, data=data, timeout=10)
        
        print(f"🔍 [DEBUG] 응답 상태 코드: {res.status_code}", flush=True)
        sys.stdout.flush()
        
        res.raise_for_status()
        token_data = res.json()
        
        access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')
        
        print(f"✅ [STEP 1] 토큰 발급 성공", flush=True)
        sys.stdout.flush()
        
        if not access_token or not new_refresh_token:
            print("❌ [FATAL] 토큰 발급 실패: 응답에 토큰이 없습니다.", flush=True)
            sys.exit(1)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ [FATAL] 토큰 발급 요청 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)
    
    print(f"\n🔍 [STEP 2] GitHub Secrets 즉시 저장 시작", flush=True)
    sys.stdout.flush()
    
    if not PA_TOKEN or not GITHUB_REPO:
        print("⚠️  [WARNING] PA_TOKEN 또는 GITHUB_REPO 없음", flush=True)
        sys.stdout.flush()
        return access_token
    
    try:
        auth = Auth.Token(PA_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(GITHUB_REPO)
        repo.create_secret("CAFE24_REFRESH_TOKEN", new_refresh_token)
        
        print(f"✅ [STEP 2] GitHub Secrets 저장 성공!", flush=True)
        sys.stdout.flush()
        
    except Exception as e:
        print(f"⚠️  [WARNING] GitHub Secrets 업데이트 실패: {e}", flush=True)
        sys.stdout.flush()
    
    print("=" * 70, flush=True)
    print("✅ 토큰 갱신 및 저장 완료", flush=True)
    print("=" * 70 + "\n", flush=True)
    sys.stdout.flush()
    
    return access_token

# ============================================================================
# 2. 네이버 블로그 크롤링
# ============================================================================
def fetch_latest_post():
    """
    네이버 블로그 RSS에서 최신 글 가져오기
    """
    print("📡 [2/4] 네이버 블로그 최신 글 크롤링 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()
    
    try:
        rss_res = requests.get(RSS_URL, timeout=10)
        rss_res.raise_for_status()
        
        rss_root = ET.fromstring(rss_res.text)
        
        item = rss_root.find('.//item')
        if not item:
            print("❌ [ERROR] RSS에 게시글이 없습니다.", flush=True)
            sys.exit(1)
        
        post_title = item.find('title').text
        post_link = item.find('link').text
        
        print(f"✅ RSS 파싱 완료", flush=True)
        print(f"   제목: {post_title}", flush=True)
        sys.stdout.flush()
        
        # logNo만 추출
        path_part = post_link.split('/')[-1]
        log_no = path_part.split('?')[0]
        
        real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
        
        print(f"✅ [2/4] 최신 글 정보 수집 완료\n", flush=True)
        sys.stdout.flush()
        
        return post_title, post_link, real_url
        
    except Exception as e:
        print(f"❌ [ERROR] RSS 파싱 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 3. 본문 및 이미지 추출
# ============================================================================
def extract_content_and_images(real_url):
    """
    네이버 블로그 본문 및 이미지 추출 (최대 5개)
    """
    print("🖼️  [3/4] 본문 및 이미지 추출 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        res = requests.get(real_url, headers=headers, timeout=15)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        content_area = soup.select_one('.se-main-container') or soup.select_one('#post-view')
        
        if not content_area:
            print("❌ [ERROR] 본문 추출 실패", flush=True)
            sys.exit(1)
        
        print(f"✅ 본문 영역 발견", flush=True)
        sys.stdout.flush()
        
        # 이미지 추출
        attachments = []
        img_tags = content_area.find_all('img')
        
        print(f"🔍 [DEBUG] 총 {len(img_tags)}개 이미지 태그 발견", flush=True)
        sys.stdout.flush()
        
        for idx, img in enumerate(img_tags):
            if idx >= 5:
                break
            
            src = img.get('src') or img.get('data-lazy-src') or img.get('data-src')
            
            if src and 'postfiles.pstatic.net' in src:
                try:
                    img_res = requests.get(src, headers=headers, timeout=10)
                    img_res.raise_for_status()
                    
                    b64_img = base64.b64encode(img_res.content).decode()
                    
                    attachments.append({
                        "filename": f"image_{idx+1}.jpg",
                        "file_data": b64_img
                    })
                    
                    print(f"   ✅ 이미지 {idx+1} 다운로드 완료 ({len(img_res.content):,} bytes)", flush=True)
                    sys.stdout.flush()
                    
                except Exception as e:
                    print(f"   ⚠️  이미지 {idx+1} 다운로드 실패: {e}", flush=True)
                    sys.stdout.flush()
        
        # 본문 텍스트
        text_content = content_area.get_text(separator='\n', strip=True)
        
        print(f"✅ 총 {len(attachments)}개 이미지 추출 완료", flush=True)
        print(f"✅ [3/4] 콘텐츠 추출 완료\n", flush=True)
        sys.stdout.flush()
        
        return text_content, attachments
        
    except Exception as e:
        print(f"❌ [ERROR] 콘텐츠 추출 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 4. 카페24 업로드 (이미지 Base64 임베드)
# ============================================================================
def upload_to_cafe24(access_token, title, content, original_link, attachments):
    """
    카페24 갤러리 게시판에 업로드 (이미지를 content에 Base64 임베드)
    """
    print("📤 [4/4] 카페24 갤러리 게시판 업로드 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()
    
    if not attachments:
        print("❌ [ERROR] 갤러리 게시판은 이미지가 필수입니다.", flush=True)
        sys.exit(1)
    
    # ✅ 이미지를 content에 직접 임베드
    image_html = ""
    for idx, att in enumerate(attachments, 1):
        image_html += f'<img src="data:image/jpeg;base64,{att["file_data"]}" alt="이미지 {idx}" style="max-width:100%;"><br>\n'
    
    final_content = f"{image_html}<br>{content}<br><br><a href='{original_link}' target='_blank'>📝 원문 보러가기</a>"
    
    print(f"🔍 [DEBUG] 이미지 {len(attachments)}개를 content에 직접 임베드", flush=True)
    sys.stdout.flush()
    
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    payload = {
        "shop_no": 1,
        "request": {
            "writer": WRITER_NAME,
            "title": title,
            "content": final_content,  # 이미지 포함된 content
            "client_ip": "127.0.0.1",
            "password": PASSWORD,
            "notice": "F",
            "fixed": "F",
            "secret": "F"
        }
    }
    
    print(f"🔍 [DEBUG] Content 길이: {len(final_content):,} 문자", flush=True)
    print(f"🔍 [DEBUG] URL: {url}", flush=True)
    sys.stdout.flush()
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\n🔍 [DEBUG] 응답 코드: {res.status_code}", flush=True)
        print(f"🔍 [DEBUG] 응답 본문: {res.text[:500]}", flush=True)
        sys.stdout.flush()
        
        if res.status_code == 201:
            print("\n" + "=" * 70, flush=True)
            print("🎉 게시글 업로드 성공! (이미지 임베드)", flush=True)
            print("=" * 70, flush=True)
            print(f"   📝 제목: {title}", flush=True)
            print(f"   ✍️  작성자: {WRITER_NAME}", flush=True)
            print(f"   🖼️  이미지: {len(attachments)}개 (Base64 임베드)", flush=True)
            print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/", flush=True)
            print("=" * 70, flush=True)
            sys.stdout.flush()
        else:
            print(f"\n❌ [ERROR] 업로드 실패 (HTTP {res.status_code})", flush=True)
            print(f"   전체 응답: {res.text}", flush=True)
            
            # Base64 임베드 실패 시, 이미지 URL만 링크로 시도
            print(f"\n⚠️  Base64 임베드 실패, 텍스트만 + 원문 링크로 재시도...", flush=True)
            sys.stdout.flush()
            
            text_only_content = f"{content}<br><br>⚠️ 이미지는 원문 링크에서 확인하세요<br><a href='{original_link}' target='_blank'>📝 원문 보러가기 (이미지 포함)</a>"
            
            payload_text = {
                "shop_no": 1,
                "request": {
                    "writer": WRITER_NAME,
                    "title": title + " [텍스트]",
                    "content": text_only_content,
                    "client_ip": "127.0.0.1",
                    "password": PASSWORD,
                    "notice": "F",
                    "fixed": "F",
                    "secret": "F"
                }
            }
            
            res2 = requests.post(url, headers=headers, json=payload_text, timeout=30)
            
            print(f"🔍 [DEBUG] 텍스트 전용 응답: {res2.status_code}", flush=True)
            print(f"🔍 [DEBUG] 텍스트 전용 본문: {res2.text[:300]}", flush=True)
            
            if res2.status_code != 201:
                print(f"❌ 텍스트 전용도 실패. 갤러리 게시판은 이미지 필수일 가능성 높음.", flush=True)
                print(f"   대안: 일반 게시판(board_no를 다른 번호로 변경) 사용 권장", flush=True)
            
            sys.stdout.flush()
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ [ERROR] 업로드 요청 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 메인 실행
# ============================================================================
def main():
    print("\n" + "=" * 70, flush=True)
    print("🚀 네이버 → 카페24 자동 포스팅 시작 (이미지 Base64 임베드)", flush=True)
    print("=" * 70 + "\n", flush=True)
    sys.stdout.flush()
    
    # 환경 변수 체크
    required_vars = [MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]
    
    if not all(required_vars):
        print("❌ [ERROR] 환경 변수가 설정되지 않았습니다.", flush=True)
        sys.exit(1)
    
    print("✅ 모든 필수 환경변수 확인 완료\n", flush=True)
    sys.stdout.flush()
    
    try:
        # 1. 토큰 갱신
        access_token = refresh_and_save_token()
        
        # 2. 최신 글 가져오기
        title, original_link, real_url = fetch_latest_post()
        
        # 3. 본문 및 이미지 추출
        content, attachments = extract_content_and_images(real_url)
        
        # 4. 카페24 업로드 (이미지 Base64 임베드)
        upload_to_cafe24(access_token, title, content, original_link, attachments)
        
        print("\n✅ 모든 작업 완료!\n", flush=True)
        sys.stdout.flush()
        
    except Exception as e:
        print(f"\n❌ [FATAL ERROR] 예상치 못한 오류: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 스크립트 진입점
# ============================================================================
if __name__ == "__main__":
    print("\n🔍 [DEBUG] main() 함수 호출\n", flush=True)
    sys.stdout.flush()
    main()
