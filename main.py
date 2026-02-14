import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, NavigableString, Tag
from github import Github, Auth
import json
from urllib.parse import urlsplit, urlunsplit

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
# 🔐 [최우선] 토큰 갱신 및 즉시 저장 (유지)
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
# 2. 네이버 블로그 RSS 최신 글 가져오기
# ============================================================================
def fetch_latest_post():
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
# 공용: 네이버 이미지 URL 정리 + 다운로드(404 방지)
# ============================================================================
def _strip_query(url: str) -> str:
    try:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except Exception:
        return url

def download_naver_image(img_url: str, referer: str) -> bytes | None:
    """
    네이버 이미지 404/차단 대응:
    - ?type=w1200 같은 쿼리 제거 시도
    - Referer 헤더 추가
    - allow_redirects True
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
        "Referer": referer,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }

    candidates = []
    if img_url:
        candidates.append(img_url)
        candidates.append(_strip_query(img_url))

    for u in candidates:
        if not u:
            continue
        try:
            r = requests.get(u, headers=headers, timeout=20, allow_redirects=True)
            if r.status_code == 200 and r.content:
                return r.content
        except Exception:
            pass
    return None

# ============================================================================
# 3. 본문 블록(텍스트/이미지) 추출 + 이미지 Base64
# ============================================================================
def extract_blocks(real_url: str):
    """
    네이버 블로그 본문에서 '텍스트/이미지'를 순서대로 블록화.
    A만 우선이라, 스타일(글자크기 등) 복원은 여기서 최소화.
    """
    print("🧱 [3/5] 본문 블록(텍스트/이미지) 추출 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36"
    }

    try:
        res = requests.get(real_url, headers=headers, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        content_area = soup.select_one('.se-main-container') or soup.select_one('#post-view')
        if not content_area:
            print("❌ [ERROR] 본문 영역을 찾지 못했습니다.", flush=True)
            sys.exit(1)

        print("✅ 본문 영역 발견", flush=True)
        sys.stdout.flush()

        blocks = []
        image_count = 0

        # 상위 블록 단위로 순회 (문단/이미지 섞임 유지 목적)
        for node in content_area.descendants:
            if isinstance(node, Tag) and node.name == "img":
                src = node.get("src") or node.get("data-lazy-src") or node.get("data-src")
                if not src:
                    continue

                # 네이버 이미지로 보이는 경우만 처리
                if ("pstatic.net" in src):
                    image_bytes = download_naver_image(src, referer=real_url)
                    if image_bytes:
                        image_count += 1
                        b64_img = base64.b64encode(image_bytes).decode()
                        blocks.append({
                            "type": "image",
                            "filename": f"image_{image_count}.jpg",
                            "base64": b64_img
                        })
                    else:
                        print(f"   ⚠️  이미지 다운로드 실패: {src}", flush=True)
                        sys.stdout.flush()

            # 텍스트는 Tag 처리보다 NavigableString 중심으로 잡되, 공백/중복 최소화
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if not text:
                    continue
                # 너무 짧은 조각 텍스트는 합치도록 block 단계에서 처리
                blocks.append({"type": "text", "text": text})

        # 텍스트 블록을 다듬어(연속 텍스트 합치기)
        merged = []
        buffer = []
        for b in blocks:
            if b["type"] == "text":
                buffer.append(b["text"])
            else:
                if buffer:
                    merged.append({"type": "text", "text": "\n".join(buffer).strip()})
                    buffer = []
                merged.append(b)
        if buffer:
            merged.append({"type": "text", "text": "\n".join(buffer).strip()})

        # 최종 점검
        img_in_blocks = sum(1 for b in merged if b["type"] == "image")
        print(f"✅ 블록 {len(merged)}개 추출 완료 (이미지 {img_in_blocks}개 포함)\n", flush=True)
        sys.stdout.flush()
        return merged

    except Exception as e:
        print(f"❌ [ERROR] 콘텐츠 추출 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 4. 카페24 Products Images 업로드 → URL
# ============================================================================
def upload_image_to_cafe24(access_token, image_data):
    """
    POST /api/v2/admin/products/images
    payload: {"requests":[{"image":"base64..."}]}
    """
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    payload = {
        "requests": [
            {
                "image": image_data["base64"]
            }
        ]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code not in [200, 201]:
            print(f"      ❌ 업로드 실패: {res.status_code} {res.text[:300]}", flush=True)
            sys.stdout.flush()
            return None

        result = res.json()
        # 응답에서 path 우선 추출
        image_url = None
        if "images" in result and result["images"]:
            image_url = result["images"][0].get("path") or result["images"][0].get("url")
        if not image_url:
            image_url = result.get("path") or result.get("url")

        return image_url

    except Exception as e:
        print(f"      ❌ 업로드 에러: {e}", flush=True)
        sys.stdout.flush()
        return None

# ============================================================================
# 5. 카페24 갤러리 게시판 글 생성 (A 해결 집중)
# ============================================================================
def create_board_article(access_token, title, html_content, thumb_url=None):
    """
    POST /api/v2/admin/boards/{board_no}/articles

    A 해결 포인트:
    - member_id = MALL_ID 로 고정 → 작성자 shop_name으로 노출되게 유도
    - password 제거 (비회원 글 느낌 제거)
    - 원본 보러가기 링크는 content에 넣지 않음
    - 썸네일(목록 메인 이미지) 후보로 attach_file_urls에 첫 이미지 URL을 넣어봄
    """
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }

    req = {
        "shop_no": 1,
        "writer": "관리자",         # required이므로 유지(표시는 member_id로 제어)
        "member_id": MALL_ID,       # ★ 핵심: mall_id면 작성자 shop_name 반환
        "title": title,
        "content": html_content,
        "client_ip": "127.0.0.1",
    }

    # ★ 갤러리 목록 썸네일 후보: 첫 이미지 URL을 첨부파일 URL로 제공
    # 문서에 attach_file_urls(이름/url) 구조가 안내됨
    if thumb_url:
        req["attach_file_urls"] = [
            {"name": "thumb.jpg", "url": thumb_url}
        ]

    payload = {"requests": [req]}

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    return res

def upload_to_cafe24(access_token, title, blocks):
    print("📤 [4/5] 카페24 이미지 업로드 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    # 1) 블록 내 이미지 업로드 후, HTML을 '원래 순서대로' 조립
    html_parts = []
    first_image_url = None
    uploaded_count = 0

    for b in blocks:
        if b["type"] == "image":
            img_url = upload_image_to_cafe24(access_token, b)
            if img_url:
                uploaded_count += 1
                if not first_image_url:
                    first_image_url = img_url
                html_parts.append(f'<p><img src="{img_url}" alt="" style="max-width:100%;height:auto;"></p>')
            else:
                # 이미지 업로드 실패 시 해당 블록은 스킵
                pass
        else:
            # 텍스트는 줄바꿈을 문단으로 변환 (A 단계: 크기/스타일 복원은 보류)
            txt = b["text"]
            # 너무 긴 텍스트 블록은 줄 단위로 쪼개서 문단화
            lines = [x.strip() for x in txt.split("\n") if x.strip()]
            for line in lines:
                html_parts.append(f"<p>{line}</p>")

    print(f"✅ 이미지 업로드 완료 (성공 {uploaded_count}개)", flush=True)
    sys.stdout.flush()

    # 갤러리 품질상 이미지 1개 이상 권장(요청하신 A 기준)
    if uploaded_count == 0:
        print("Error: ❌ [ERROR] 이미지가 0개입니다. (갤러리/콘텐츠 품질상 최소 1개 권장)", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print("\n📤 [5/5] 게시글 생성 시작 (A 해결 집중)", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    final_html = "\n".join(html_parts)

    # ★ A-3: 원본 보러가기 링크는 넣지 않음 (요청사항)
    # (따라서 여기서는 original_link를 아예 사용하지 않습니다.)

    res = create_board_article(
        access_token=access_token,
        title=title,
        html_content=final_html,
        thumb_url=first_image_url
    )

    print(f"          응답 코드: {res.status_code}", flush=True)
    print(f"          응답 본문: {res.text[:500]}", flush=True)
    sys.stdout.flush()

    if res.status_code == 201:
        print("\n" + "=" * 70, flush=True)
        print("🎉 게시글 업로드 성공! (A 해결 버전)", flush=True)
        print("=" * 70, flush=True)
        print(f"   📝 제목: {title}", flush=True)
        print(f"   🖼️  이미지: {uploaded_count}개", flush=True)
        print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/", flush=True)
        print("=" * 70, flush=True)
        sys.stdout.flush()
    else:
        print("\n❌ [ERROR] 게시글 생성 실패", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 메인
# ============================================================================
def main():
    print("\n" + "=" * 70, flush=True)
    print("🚀 네이버 → 카페24 자동 포스팅 (A 해결 집중)", flush=True)
    print("=" * 70 + "\n", flush=True)
    sys.stdout.flush()

    required_vars = [MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]
    if not all(required_vars):
        print("❌ [ERROR] 환경 변수가 설정되지 않았습니다.", flush=True)
        sys.exit(1)

    print("✅ 모든 필수 환경변수 확인 완료\n", flush=True)
    sys.stdout.flush()

    # 1) 토큰 갱신
    access_token = refresh_and_save_token()

    # 2) 최신 글
    title, original_link, real_url = fetch_latest_post()

    # 3) 블록 추출
    blocks = extract_blocks(real_url)

    # 4~5) 이미지 업로드 + 게시글 생성
    upload_to_cafe24(access_token, title, blocks)

    print("\n✅ 모든 작업 완료!\n", flush=True)
    sys.stdout.flush()

if __name__ == "__main__":
    print("\n🔍 [DEBUG] main() 함수 호출\n", flush=True)
    sys.stdout.flush()
    main()
