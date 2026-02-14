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
    print("📡 [2/5] 네이버 블로그 최신 글 크롤링 시작", flush=True)
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
        
        print(f"✅ [2/5] 최신 글 정보 수집 완료\n", flush=True)
        sys.stdout.flush()
        
        return post_title, post_link, real_url
        
    except Exception as e:
        print(f"❌ [ERROR] RSS 파싱 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 3. 본문 및 이미지 추출 (Base64 변환)
# ============================================================================
def extract_content_and_images(real_url):
    """
    네이버 블로그 본문 및 이미지 추출 (Base64 변환)
    """
    print("🖼️  [3/5] 본문 및 이미지 추출 시작", flush=True)
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
        
        # 이미지 추출 및 Base64 변환
        images = []
        img_tags = content_area.find_all('img')
        
        print(f"🔍 [DEBUG] 총 {len(img_tags)}개 이미지 태그 발견", flush=True)
        sys.stdout.flush()
        
        for idx, img in enumerate(img_tags):
            if idx >= 1:  # ⚠️ 테스트용으로 1개만!
                break
            
            src = img.get('src') or img.get('data-lazy-src') or img.get('data-src')
            
            if src and 'postfiles.pstatic.net' in src:
                try:
                    img_res = requests.get(src, headers=headers, timeout=10)
                    img_res.raise_for_status()
                    
                    # Base64 변환
                    b64_img = base64.b64encode(img_res.content).decode()
                    
                    images.append({
                        "filename": f"image_{idx+1}.jpg",
                        "base64": b64_img
                    })
                    
                    print(f"   ✅ 이미지 {idx+1} 다운로드 완료 ({len(img_res.content):,} bytes)", flush=True)
                    sys.stdout.flush()
                    
                except Exception as e:
                    print(f"   ⚠️  이미지 {idx+1} 다운로드 실패: {e}", flush=True)
                    sys.stdout.flush()
        
        # 본문 텍스트
        text_content = content_area.get_text(separator='\n', strip=True)
        
        print(f"✅ 총 {len(images)}개 이미지 추출 완료 (테스트용)", flush=True)
        print(f"✅ [3/5] 콘텐츠 추출 완료\n", flush=True)
        sys.stdout.flush()
        
        return text_content, images
        
    except Exception as e:
        print(f"❌ [ERROR] 콘텐츠 추출 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 4. 이미지 업로드 - 8가지 패턴 자동 테스트
# ============================================================================
def upload_image_to_cafe24_auto_test(access_token, image_data, sort_order=1):
    """
    8가지 payload 패턴을 순차적으로 자동 테스트
    """
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    
    # ✅ 8가지 패턴
    patterns = [
        {
            "name": "패턴1: request.image (문자열)",
            "payload": {
                "request": {
                    "image": image_data["base64"]
                }
            }
        },
        {
            "name": "패턴2: request.image.image + sort",
            "payload": {
                "request": {
                    "image": {
                        "image": image_data["base64"],
                        "sort": sort_order
                    }
                }
            }
        },
        {
            "name": "패턴3: image (직접, 문자열)",
            "payload": {
                "image": image_data["base64"]
            }
        },
        {
            "name": "패턴4: image.image (객체)",
            "payload": {
                "image": {
                    "image": image_data["base64"]
                }
            }
        },
        {
            "name": "패턴5: request.images (배열)",
            "payload": {
                "request": {
                    "images": [
                        {
                            "image": image_data["base64"],
                            "sort": sort_order
                        }
                    ]
                }
            }
        },
        {
            "name": "패턴6: shop_no + request.image",
            "payload": {
                "shop_no": 1,
                "request": {
                    "image": image_data["base64"]
                }
            }
        },
        {
            "name": "패턴7: image + filename",
            "payload": {
                "image": image_data["base64"],
                "filename": image_data["filename"]
            }
        },
        {
            "name": "패턴8: request.image + filename",
            "payload": {
                "request": {
                    "image": image_data["base64"],
                    "filename": image_data["filename"]
                }
            }
        }
    ]
    
    print(f"\n      🔍 총 {len(patterns)}가지 패턴 자동 테스트 시작", flush=True)
    print("      " + "="*60, flush=True)
    sys.stdout.flush()
    
    for idx, pattern in enumerate(patterns, 1):
        print(f"\n      [{idx}/{len(patterns)}] {pattern['name']}", flush=True)
        sys.stdout.flush()
        
        try:
            res = requests.post(url, headers=headers, json=pattern['payload'], timeout=30)
            
            print(f"          응답 코드: {res.status_code}", flush=True)
            
            if res.status_code in [200, 201]:
                print(f"          ✅ 성공!", flush=True)
                print(f"          응답: {res.text[:200]}", flush=True)
                sys.stdout.flush()
                
                # URL 추출
                result = res.json()
                image_url = None
                
                if 'image' in result:
                    if isinstance(result['image'], dict):
                        image_url = result['image'].get('url') or result['image'].get('image_url')
                    elif isinstance(result['image'], str):
                        image_url = result['image']
                elif 'url' in result:
                    image_url = result['url']
                
                if image_url:
                    print(f"\n      🎉 성공한 패턴: {pattern['name']}", flush=True)
                    print(f"      이미지 URL: {image_url}", flush=True)
                    sys.stdout.flush()
                    return image_url
                else:
                    print(f"          ⚠️  URL 없음: {result}", flush=True)
                    
            else:
                print(f"          ❌ 실패: {res.text[:150]}", flush=True)
                
        except Exception as e:
            print(f"          ❌ 에러: {e}", flush=True)
        
        sys.stdout.flush()
    
    print(f"\n      ❌ 모든 패턴 실패", flush=True)
    sys.stdout.flush()
    return None

# ============================================================================
# 5. 카페24 갤러리 게시판에 게시글 업로드
# ============================================================================
def upload_to_cafe24(access_token, title, content, original_link, images):
    """
    카페24 갤러리 게시판에 업로드
    """
    print("📤 [4/5] 이미지 자동 패턴 테스트 업로드 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()
    
    if not images:
        print("❌ [ERROR] 이미지가 없습니다.", flush=True)
        sys.exit(1)
    
    # 각 이미지를 8가지 패턴으로 자동 테스트
    image_urls = []
    
    for idx, img_data in enumerate(images, 1):
        print(f"   🔄 이미지 {idx}/{len(images)} 업로드 (자동 패턴 테스트)...", flush=True)
        sys.stdout.flush()
        
        url = upload_image_to_cafe24_auto_test(access_token, img_data, sort_order=idx)
        if url:
            image_urls.append(url)
            break  # 첫 번째 성공하면 중단
    
    if not image_urls:
        print("❌ [ERROR] 모든 패턴으로 업로드 실패", flush=True)
        sys.exit(1)
    
    print(f"\n✅ 성공! 이미지 업로드 완료", flush=True)
    print(f"   성공한 이미지 URL: {image_urls[0]}", flush=True)
    sys.stdout.flush()
    
    print("\n🎉 패턴 발견! 이제 실제 게시글 생성은 스킵합니다.", flush=True)
    print("   성공한 패턴으로 전체 코드를 수정하세요.", flush=True)
    sys.stdout.flush()

# ============================================================================
# 메인 실행
# ============================================================================
def main():
    print("\n" + "=" * 70, flush=True)
    print("🚀 카페24 이미지 API 자동 패턴 테스트", flush=True)
    print("=" * 70 + "\n", flush=True)
    sys.stdout.flush()
    
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
        
        # 3. 본문 및 이미지 추출 (1개만!)
        content, images = extract_content_and_images(real_url)
        
        # 4. 자동 패턴 테스트
        upload_to_cafe24(access_token, title, content, original_link, images)
        
        print("\n✅ 테스트 완료!\n", flush=True)
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
