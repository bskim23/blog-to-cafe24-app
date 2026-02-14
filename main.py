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
print("=" * 70)
print("🔍 [DEBUG] 스크립트 시작 - 모든 라이브러리 import 성공")
print("=" * 70)

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
WRITER_NAME = "메디힐리"  # ← 변경!
RSS_URL = "https://rss.blog.naver.com/mediheally_lab.xml"

# ============================================================================
# 🔍 디버그: 환경변수 확인
# ============================================================================
print("\n🔍 [DEBUG] 환경변수 로드 상태:")
print(f"   MALL_ID          : {'✅ ' + MALL_ID if MALL_ID else '❌ None'}")
print(f"   CLIENT_ID        : {'✅ ' + CLIENT_ID[:10] + '...' if CLIENT_ID else '❌ None'}")
print(f"   CLIENT_SECRET    : {'✅ ' + CLIENT_SECRET[:10] + '...' if CLIENT_SECRET else '❌ None'}")
print(f"   REFRESH_TOKEN    : {'✅ ' + REFRESH_TOKEN[:20] + '...' if REFRESH_TOKEN else '❌ None'}")
print(f"   PA_TOKEN         : {'✅ 있음' if PA_TOKEN else '❌ None'}")
print(f"   GITHUB_REPO      : {'✅ ' + GITHUB_REPO if GITHUB_REPO else '❌ None'}")
print(f"   BOARD_NO         : {BOARD_NO}")
print(f"   PASSWORD         : {PASSWORD}")
print(f"   WRITER_NAME      : {WRITER_NAME}")
print(f"   RSS_URL          : {RSS_URL}")
print("=" * 70 + "\n")

# ============================================================================
# 🔐 [최우선] 토큰 갱신 및 즉시 저장
# ============================================================================
def refresh_and_save_token():
    """
    ⚠️ 최우선 작업: Access Token 발급 및 새 Refresh Token 즉시 저장
    이 작업이 완료되어야만 다음 단계로 진행
    """
    print("=" * 70)
    print("🔐 [최우선] 토큰 갱신 및 저장 시작")
    print("=" * 70)
    
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    print(f"🔍 [DEBUG] API URL: {url}")
    print(f"🔍 [DEBUG] Auth Header 생성 완료")
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    try:
        print(f"\n🔍 [STEP 1] POST 요청 전송 중...")
        res = requests.post(url, headers=headers, data=data, timeout=10)
        
        print(f"🔍 [DEBUG] 응답 상태 코드: {res.status_code}")
        print(f"🔍 [DEBUG] 응답 내용: {res.text[:200]}...")
        
        res.raise_for_status()
        token_data = res.json()
        
        access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')
        
        print(f"🔍 [DEBUG] Access Token: {'✅ 발급됨 (' + access_token[:20] + '...)' if access_token else '❌ 없음'}")
        print(f"🔍 [DEBUG] New Refresh Token: {'✅ 발급됨 (' + new_refresh_token[:20] + '...)' if new_refresh_token else '❌ 없음'}")
        
        if not access_token or not new_refresh_token:
            print("❌ [FATAL] 토큰 발급 실패: 응답에 토큰이 없습니다.")
            sys.exit(1)
        
        print("✅ [STEP 1] 토큰 발급 성공")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ [FATAL] 토큰 발급 요청 실패: {e}")
        print(f"🔍 [DEBUG] Exception Type: {type(e).__name__}")
        sys.exit(1)
    
    print(f"\n🔍 [STEP 2] GitHub Secrets 즉시 저장 시작")
    print(f"   PA_TOKEN 존재: {'✅' if PA_TOKEN else '❌'}")
    print(f"   GITHUB_REPO: {GITHUB_REPO}")
    
    if not PA_TOKEN or not GITHUB_REPO:
        print("⚠️  [WARNING] PA_TOKEN 또는 GITHUB_REPO 없음 - Secrets 업데이트 불가")
        print(f"⚠️  [MANUAL] 수동으로 업데이트 필요:")
        print(f"   새 Refresh Token: {new_refresh_token}")
        print("\n✅ Access Token만 사용하여 계속 진행\n")
        return access_token
    
    try:
        print(f"🔍 [DEBUG] PyGithub 인증 중...")
        auth = Auth.Token(PA_TOKEN)
        g = Github(auth=auth)
        
        print(f"🔍 [DEBUG] Repository 접근 중: {GITHUB_REPO}")
        repo = g.get_repo(GITHUB_REPO)
        
        print(f"🔍 [DEBUG] Secret 'CAFE24_REFRESH_TOKEN' 업데이트 중...")
        repo.create_secret("CAFE24_REFRESH_TOKEN", new_refresh_token)
        
        print(f"✅ [STEP 2] GitHub Secrets 저장 성공!")
        print(f"   업데이트된 Secret: CAFE24_REFRESH_TOKEN")
        print(f"   새 값: {new_refresh_token[:20]}...")
        
    except Exception as e:
        print(f"❌ [ERROR] GitHub Secrets 업데이트 실패: {e}")
        print(f"🔍 [DEBUG] Exception Type: {type(e).__name__}")
        print(f"\n⚠️  [CRITICAL] 수동으로 즉시 업데이트하세요:")
        print(f"   Secret 이름: CAFE24_REFRESH_TOKEN")
        print(f"   새 값: {new_refresh_token}")
        print(f"\n⚠️  이전 Refresh Token은 이미 무효화되었습니다!")
        
        import traceback
        print(f"🔍 [DEBUG] Traceback:\n{traceback.format_exc()}")
        
        print(f"\n⚠️  Access Token은 발급되었으므로 이번 실행은 계속 진행합니다.")
        print(f"   하지만 다음 실행 전에 반드시 수동 업데이트 필요!\n")
    
    print("=" * 70)
    print("✅ 토큰 갱신 및 저장 완료 - 안전하게 다음 단계 진행 가능")
    print("=" * 70 + "\n")
    
    return access_token

# ============================================================================
# 2. 네이버 블로그 크롤링
# ============================================================================
def fetch_latest_post():
    """
    네이버 블로그 RSS에서 최신 글 가져오기
    """
    print("📡 [2/4] 네이버 블로그 최신 글 크롤링 시작")
    print("-" * 70)
    
    try:
        print(f"🔍 [DEBUG] RSS URL: {RSS_URL}")
        print(f"🔍 [DEBUG] RSS 요청 전송 중...")
        
        rss_res = requests.get(RSS_URL, timeout=10)
        rss_res.raise_for_status()
        
        print(f"🔍 [DEBUG] RSS 응답 상태: {rss_res.status_code}")
        print(f"🔍 [DEBUG] RSS 파싱 중...")
        
        rss_root = ET.fromstring(rss_res.text)
        
        item = rss_root.find('.//item')
        if not item:
            print("❌ [ERROR] RSS에 게시글이 없습니다.")
            sys.exit(1)
        
        post_title = item.find('title').text
        post_link = item.find('link').text
        
        print(f"✅ RSS 파싱 완료")
        print(f"   제목: {post_title}")
        print(f"   원본 링크: {post_link}")
        
        # logNo만 추출 (쿼리 파라미터 제거)
        path_part = post_link.split('/')[-1]
        log_no = path_part.split('?')[0]
        
        print(f"🔍 [DEBUG] 추출된 logNo: {log_no}")
        
        real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"
        
        print(f"🔍 [DEBUG] 실제 URL 생성: {real_url}")
        print(f"✅ [2/4] 최신 글 정보 수집 완료\n")
        
        return post_title, post_link, real_url
        
    except Exception as e:
        print(f"❌ [ERROR] RSS 파싱 실패: {e}")
        print(f"🔍 [DEBUG] Exception Type: {type(e).__name__}")
        import traceback
        print(f"🔍 [DEBUG] Traceback:\n{traceback.format_exc()}")
        sys.exit(1)

# ============================================================================
# 3. 본문 및 이미지 추출
# ============================================================================
def extract_content_and_images(real_url):
    """
    네이버 블로그 본문 및 이미지 추출 (최대 5개)
    """
    print("🖼️  [3/4] 본문 및 이미지 추출 시작")
    print("-" * 70)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        print(f"🔍 [DEBUG] 페이지 요청: {real_url}")
        res = requests.get(real_url, headers=headers, timeout=15)
        res.raise_for_status()
        
        print(f"🔍 [DEBUG] 응답 상태: {res.status_code}")
        print(f"🔍 [DEBUG] HTML 파싱 중...")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 본문 영역 찾기
        print(f"🔍 [DEBUG] 본문 영역 탐색 중...")
        content_area = soup.select_one('.se-main-container') or soup.select_one('#post-view')
        
        if not content_area:
            print("❌ [ERROR] 본문 추출 실패: 네이버 블로그 구조를 찾을 수 없습니다.")
            print(f"🔍 [DEBUG] 페이지 HTML 길이: {len(res.text)}")
            sys.exit(1)
        
        print(f"✅ 본문 영역 발견")
        
        # 이미지 추출 (최대 5개)
        print(f"🔍 [DEBUG] 이미지 태그 탐색 중...")
        attachments = []
        img_tags = content_area.find_all('img')
        
        print(f"🔍 [DEBUG] 총 {len(img_tags)}개 이미지 태그 발견")
        
        for idx, img in enumerate(img_tags):
            if idx >= 5:
                print(f"🔍 [DEBUG] 최대 5개 제한으로 중단")
                break
            
            src = img.get('src') or img.get('data-lazy-src') or img.get('data-src')
            
            print(f"🔍 [DEBUG] 이미지 {idx+1}: {src[:50] if src else 'None'}...")
            
            if src and 'postfiles.pstatic.net' in src:
                try:
                    print(f"   → 다운로드 시도 중...")
                    img_res = requests.get(src, headers=headers, timeout=10)
                    img_res.raise_for_status()
                    
                    # Base64 인코딩
                    b64_img = base64.b64encode(img_res.content).decode()
                    
                    attachments.append({
                        "filename": f"image_{idx+1}.jpg",
                        "file_data": b64_img
                    })
                    
                    print(f"   ✅ 이미지 {idx+1} 다운로드 완료 ({len(img_res.content):,} bytes, Base64: {len(b64_img):,} chars)")
                    
                except Exception as e:
                    print(f"   ⚠️  이미지 {idx+1} 다운로드 실패: {e}")
            else:
                print(f"   → 건너뜀 (네이버 이미지 아님)")
        
        # 본문 텍스트
        print(f"\n🔍 [DEBUG] 본문 텍스트 추출 중...")
        text_content = content_area.get_text(separator='\n', strip=True)
        text_preview = text_content[:100].replace('\n', ' ')
        
        print(f"✅ 본문 추출 완료")
        print(f"   길이: {len(text_content):,}자")
        print(f"   미리보기: {text_preview}...")
        print(f"   총 {len(attachments)}개 이미지 추출 완료")
        print(f"✅ [3/4] 콘텐츠 추출 완료\n")
        
        return text_content, attachments
        
    except Exception as e:
        print(f"❌ [ERROR] 콘텐츠 추출 실패: {e}")
        print(f"🔍 [DEBUG] Exception Type: {type(e).__name__}")
        import traceback
        print(f"🔍 [DEBUG] Traceback:\n{traceback.format_exc()}")
        sys.exit(1)

# ============================================================================
# 4. 카페24 업로드
# ============================================================================
def upload_to_cafe24(access_token, title, content, original_link, attachments):
    """
    카페24 갤러리 게시판에 업로드
    """
    print("📤 [4/4] 카페24 갤러리 게시판 업로드 시작")
    print("-" * 70)
    
    # 이미지 없으면 업로드 불가
    print(f"🔍 [DEBUG] 이미지 개수 확인: {len(attachments)}개")
    
    if not attachments:
        print("❌ [ERROR] 갤러리 게시판은 최소 1개의 이미지가 필요합니다.")
        sys.exit(1)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔍 디버깅: 각 이미지 파일 크기 확인
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n🔍 [DEBUG] 이미지 상세 정보:")
    for idx, att in enumerate(attachments):
        print(f"   이미지 {idx+1}:")
        print(f"      filename: {att['filename']}")
        print(f"      Base64 길이: {len(att['file_data']):,} chars")
        # Base64 → 원본 크기 추정 (Base64는 약 1.33배 커짐)
        original_size = len(att['file_data']) * 3 / 4
        print(f"      추정 원본 크기: {original_size:,.0f} bytes ({original_size/1024/1024:.2f} MB)")
    
    # 본문 구성 (원문 링크 추가)
    final_content = f"{content}\n\n<br><br><a href='{original_link}' target='_blank'>📝 원문 보러가기</a>"
    
    print(f"\n🔍 [DEBUG] 최종 본문 길이: {len(final_content):,}자")
    
    payload = {
        "shop_no": 1,
        "request": {
            "board_no": BOARD_NO,
            "title": title,
            "content": final_content,
            "writer": WRITER_NAME,  # ← "메디힐리"
            "password": PASSWORD,
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments
        }
    }
    
    print(f"\n🔍 [DEBUG] Payload 구성 완료:")
    print(f"   shop_no: 1")
    print(f"   board_no: {BOARD_NO}")
    print(f"   title: {title}")
    print(f"   content 길이: {len(final_content)} chars")
    print(f"   writer: {WRITER_NAME}")  # ← "메디힐리"
    print(f"   password: {PASSWORD}")
    print(f"   is_notice: F")
    print(f"   is_secret: F")
    print(f"   attachments: {len(attachments)}개")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔍 디버깅: Payload 샘플 출력 (Base64 제외)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    debug_payload = {
        "shop_no": 1,
        "request": {
            "board_no": BOARD_NO,
            "title": title,
            "content": final_content[:100] + "...",
            "writer": WRITER_NAME,
            "password": PASSWORD,
            "is_notice": "F",
            "is_secret": "F",
            "attachments": [
                {
                    "filename": att["filename"],
                    "file_data": f"<Base64 {len(att['file_data'])} chars>"
                }
                for att in attachments
            ]
        }
    }
    print(f"\n🔍 [DEBUG] Payload 구조 (Base64 생략):")
    print(json.dumps(debug_payload, indent=2, ensure_ascii=False))
    
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n🔍 [DEBUG] API URL: {url}")
    print(f"🔍 [DEBUG] Headers:")
    print(f"   Authorization: Bearer {access_token[:20]}...")
    print(f"   Content-Type: application/json")
    print(f"\n🔍 [DEBUG] POST 요청 전송 중...")
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\n🔍 [DEBUG] 응답 상태 코드: {res.status_code}")
        print(f"🔍 [DEBUG] 응답 헤더:")
        for key, value in res.headers.items():
            print(f"   {key}: {value}")
        print(f"\n🔍 [DEBUG] 응답 전체 내용:")
        print(res.text)
        
        if res.status_code == 201:
            print("\n" + "=" * 70)
            print("🎉 게시글 업로드 성공!")
            print("=" * 70)
            print(f"   📝 제목: {title}")
            print(f"   ✍️  작성자: {WRITER_NAME}")
            print(f"   🖼️  이미지: {len(attachments)}개")
            print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/")
            print("=" * 70)
            print(f"✅ [4/4] 업로드 완료\n")
        else:
            print(f"\n❌ [ERROR] 업로드 실패 (HTTP {res.status_code})")
            print(f"   응답 전체 내용:")
            
            # JSON 파싱 시도
            try:
                error_json = res.json()
                print(json.dumps(error_json, indent=2, ensure_ascii=False))
            except:
                print(res.text)
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 422 에러일 경우 추가 안내
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if res.status_code == 422:
                print(f"\n⚠️  [422 에러 가능한 원인]")
                print(f"   1. 필수 필드 누락 또는 형식 오류")
                print(f"   2. 이미지 크기 제한 초과 (각 파일 또는 전체 용량)")
                print(f"   3. writer 필드 값이 게시판 설정과 불일치")
                print(f"   4. attachments 배열 형식 오류")
                print(f"   5. 게시판 권한 문제")
                print(f"\n   위 Payload 구조를 확인하세요.")
            
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ [ERROR] 업로드 요청 실패: {e}")
        print(f"🔍 [DEBUG] Exception Type: {type(e).__name__}")
        import traceback
        print(f"🔍 [DEBUG] Traceback:\n{traceback.format_exc()}")
        sys.exit(1)

# ============================================================================
# 메인 실행
# ============================================================================
def main():
    print("\n" + "=" * 70)
    print("🚀 네이버 → 카페24 자동 포스팅 시작")
    print("=" * 70 + "\n")
    
    # 환경 변수 체크
    print("🔍 [DEBUG] 필수 환경변수 검증 중...")
    required_vars = [MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]
    
    if not all(required_vars):
        print("❌ [ERROR] 환경 변수가 설정되지 않았습니다.")
        print("   GitHub Secrets를 확인하세요:")
        print(f"   MALL_ID: {'✅' if MALL_ID else '❌'}")
        print(f"   CLIENT_ID: {'✅' if CLIENT_ID else '❌'}")
        print(f"   CLIENT_SECRET: {'✅' if CLIENT_SECRET else '❌'}")
        print(f"   REFRESH_TOKEN: {'✅' if REFRESH_TOKEN else '❌'}")
        sys.exit(1)
    
    print("✅ 모든 필수 환경변수 확인 완료\n")
    
    try:
        # [최우선] 토큰 갱신 및 저장
        print("🔍 [DEBUG] [최우선 작업] 토큰 갱신 및 저장 호출")
        access_token = refresh_and_save_token()
        
        print("✅ 토큰 안전하게 확보됨 - 이제 나머지 작업 진행\n")
        
        # 2. 최신 글 가져오기
        print("🔍 [DEBUG] Step 2: 최신 글 가져오기 호출")
        title, original_link, real_url = fetch_latest_post()
        
        # 3. 본문 및 이미지 추출
        print("🔍 [DEBUG] Step 3: 본문 및 이미지 추출 호출")
        content, attachments = extract_content_and_images(real_url)
        
        # 4. 카페24 업로드
        print("🔍 [DEBUG] Step 4: 카페24 업로드 호출")
        upload_to_cafe24(access_token, title, content, original_link, attachments)
        
        print("\n" + "=" * 70)
        print("✅ 모든 작업 완료!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ [FATAL ERROR] 예상치 못한 오류 발생: {e}")
        print(f"🔍 [DEBUG] Exception Type: {type(e).__name__}")
        import traceback
        print(f"🔍 [DEBUG] Traceback:\n{traceback.format_exc()}")
        print(f"\n⚠️  하지만 토큰은 이미 안전하게 저장되었으므로")
        print(f"   다음 실행 시 새 토큰으로 재시도 가능합니다.")
        sys.exit(1)

# ============================================================================
# 스크립트 진입점
# ============================================================================
print("\n🔍 [DEBUG] 스크립트 진입점 도달")
print(f"🔍 [DEBUG] __name__ = {__name__}")

if __name__ == "__main__":
    print("🔍 [DEBUG] main() 함수 호출 직전\n")
    main()
    print("\n🔍 [DEBUG] main() 함수 종료")
