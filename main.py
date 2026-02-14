import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from github import Github, Auth
import json
import re
import html
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

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
# 2. 네이버 블로그 RSS 최신 글
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
# 네이버 이미지 URL 고해상도 강제
# ============================================================================
def force_large_naver_image(url: str, target_w: int = 2000) -> str:
    if not url:
        return url

    # 1) 문자열 치환: type=w###
    url2 = re.sub(r'(type=)w\d+', rf'\1w{target_w}', url)

    # 2) 쿼리 기반 보정
    try:
        pr = urlparse(url2)
        q = dict(parse_qsl(pr.query, keep_blank_values=True))

        if "type" in q and re.match(r"w\d+", q["type"]):
            q["type"] = f"w{target_w}"
        elif "type" not in q:
            if "pstatic.net" in url2:
                q["type"] = f"w{target_w}"

        new_query = urlencode(q, doseq=True)
        url2 = urlunparse(pr._replace(query=new_query))
    except Exception:
        pass

    return url2


def pick_best_img_url(img_tag):
    candidates = [
        img_tag.get('data-original'),
        img_tag.get('data-ori-src'),
        img_tag.get('data-src'),
        img_tag.get('data-lazy-src'),
        img_tag.get('data-image-src'),
        img_tag.get('data-img-src'),
        img_tag.get('src'),  # fallback
    ]
    candidates = [c for c in candidates if c]
    if not candidates:
        return None
    return force_large_naver_image(candidates[0], target_w=2000)

# ============================================================================
# 텍스트/중복 처리 + 헤딩 승격
# ============================================================================
def clean_text_block(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    return text

def normalize_text_for_dedupe(text: str) -> str:
    t = text.strip()
    t = re.sub(r"\r\n?", "\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t

def dedupe_key(text: str) -> str:
    t = normalize_text_for_dedupe(text)
    if len(t) > 400:
        t = t[:400]
    return t

def should_promote_to_heading(text: str) -> bool:
    t = text.strip()
    if "\n" in t:
        return False
    if 3 <= len(t) <= 28 and t.endswith(":"):
        return True
    if re.match(r"^(STEP|Step)\s*\d+", t):
        return True
    if re.match(r"^[✅✔■]\s*", t):
        return True
    return False

def render_text_block(text: str, tag: str) -> str:
    text = clean_text_block(text)
    esc = html.escape(text).replace("\n", "<br>\n")

    # 네이버에서 헤더로 잡힌 건 카페24에서도 헤더로
    if tag in ("h1", "h2"):
        return f"<h2>{esc}</h2>"
    if tag == "h3":
        return f"<h3>{esc}</h3>"

    # DOM이 p여도 패턴이면 소제목으로 승격
    if tag == "p" and should_promote_to_heading(text):
        return f"<h3>{esc}</h3>"

    # 리스트는 최소한의 불릿
    if tag == "li":
        return f"<p>• {esc}</p>"

    return f"<p>{esc}</p>"

def iter_blocks_from_content_area(content_area):
    """
    ✅ 중복 방지 핵심:
    - div/figure 래퍼는 텍스트 추출 대상에서 제외
    - 의미 있는 태그(p/h1~h3/li/img)만 탐색
    - 동일 텍스트는 seen으로 제거
    """
    nodes = content_area.find_all(['h1', 'h2', 'h3', 'p', 'li', 'img'], recursive=True)

    seen = set()

    for node in nodes:
        if node.name == 'img':
            yield {"type": "image", "img_tag": node}
            continue

        txt = node.get_text(separator="\n", strip=True)
        txt = clean_text_block(txt)
        if not txt:
            continue

        key = dedupe_key(txt)
        if key in seen:
            continue
        seen.add(key)

        yield {"type": "text", "text": txt, "tag": node.name}

def merge_text_blocks(blocks, max_chars=900):
    """
    연속 text 블록을 적당히 합쳐 문단 호흡 복원 (이미지 만나면 끊음)
    """
    merged = []
    buffer = []
    buffer_tag = None  # 병합 시 대표 tag (헤더는 병합하지 않도록)

    def flush():
        nonlocal buffer_tag
        if not buffer:
            return
        merged.append({"type": "text", "text": "\n\n".join(buffer), "tag": buffer_tag or "p"})
        buffer.clear()
        buffer_tag = None

    for b in blocks:
        if b["type"] == "image":
            flush()
            merged.append(b)
            continue

        t = b["text"]
        tag = b.get("tag", "p")

        # 헤더는 단독 유지
        if tag in ("h1", "h2", "h3"):
            flush()
            merged.append(b)
            continue

        if not buffer:
            buffer.append(t)
            buffer_tag = tag
            continue

        if sum(len(x) for x in buffer) + len(t) > max_chars:
            flush()
            buffer.append(t)
            buffer_tag = tag
        else:
            buffer.append(t)

    flush()
    return merged

# ============================================================================
# 본문 블록 추출 (text/image 섞인 순서 유지)
# ============================================================================
def extract_blocks(real_url):
    """
    네이버 블로그 본문을 '블록(text/image) 순서'로 추출
    """
    print("🖼️  [3/5] 본문 및 이미지 블록 추출 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    nav_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        res = requests.get(real_url, headers=nav_headers, timeout=15)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, 'html.parser')
        content_area = soup.select_one('.se-main-container') or soup.select_one('#post-view')

        if not content_area:
            print("❌ [ERROR] 본문 추출 실패", flush=True)
            sys.exit(1)

        print("✅ 본문 영역 발견", flush=True)
        sys.stdout.flush()

        raw_blocks = list(iter_blocks_from_content_area(content_area))[:600]
        blocks = merge_text_blocks(raw_blocks)

        t_cnt = sum(1 for b in blocks if b["type"] == "text")
        i_cnt = sum(1 for b in blocks if b["type"] == "image")
        print(f"🔍 [DEBUG] 블록 수(최종): text={t_cnt}, image={i_cnt}", flush=True)
        sys.stdout.flush()

        return blocks, nav_headers

    except Exception as e:
        print(f"❌ [ERROR] 콘텐츠 추출 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 4. 이미지를 카페24 Products Images API로 업로드 (requests[].image 유지)
# ============================================================================
def upload_image_to_cafe24(access_token, image_data):
    """
    카페24 Products Images API로 이미지 업로드 → 이미지 URL 받기
    """
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "requests": [
            {
                "image": image_data["base64"]
            }
        ]
    }

    print(f"      🔍 Payload 구조: requests[].image", flush=True)
    sys.stdout.flush()

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"      🔍 업로드 응답 코드: {res.status_code}", flush=True)
        sys.stdout.flush()

        if res.status_code in [200, 201]:
            result = res.json()

            image_url = None
            if 'images' in result and isinstance(result['images'], list) and len(result['images']) > 0:
                img_obj = result['images'][0]
                image_url = img_obj.get('path') or img_obj.get('url') or img_obj.get('image_url')
            elif 'path' in result:
                image_url = result['path']
            elif 'url' in result:
                image_url = result['url']

            if image_url:
                print(f"      ✅ 이미지 URL: {image_url}", flush=True)
                sys.stdout.flush()
                return image_url

            print(f"      ⚠️  URL 추출 실패: {json.dumps(result, ensure_ascii=False)[:300]}", flush=True)
            sys.stdout.flush()
            return None

        print(f"      ❌ 업로드 실패: {res.text[:300]}", flush=True)
        sys.stdout.flush()
        return None

    except Exception as e:
        print(f"      ❌ 에러: {e}", flush=True)
        sys.stdout.flush()
        return None

# ============================================================================
# 5. 카페24 갤러리 게시판 업로드 (블록 순서 유지 + 헤딩 반영)
# ============================================================================
def upload_to_cafe24(access_token, title, blocks, original_link, nav_headers):
    print("📤 [4/5] 블록 순서대로 카페24 콘텐츠 구성 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    html_parts = []
    uploaded = 0
    max_images = 20  # 필요 시 조정

    for b in blocks:
        if b["type"] == "text":
            html_parts.append(render_text_block(b["text"], b.get("tag", "p")))
            continue

        # image
        if uploaded >= max_images:
            continue

        img_tag = b["img_tag"]
        src = pick_best_img_url(img_tag)
        if not src:
            continue

        if not ("pstatic.net" in src or "naver.net" in src):
            continue

        try:
            img_res = requests.get(src, headers=nav_headers, timeout=15)
            img_res.raise_for_status()
            size = len(img_res.content)

            # 썸네일 의심 시 재시도(더 큰 w)
            if size < 30_000:
                src2 = force_large_naver_image(src, target_w=3000)
                if src2 != src:
                    img_res2 = requests.get(src2, headers=nav_headers, timeout=15)
                    if img_res2.ok and len(img_res2.content) > size:
                        img_res = img_res2
                        size = len(img_res.content)

            if size < 30_000:
                print(f"   ⚠️  썸네일로 의심(스킵): {size:,} bytes", flush=True)
                sys.stdout.flush()
                continue

            b64_img = base64.b64encode(img_res.content).decode()
            image_url = upload_image_to_cafe24(access_token, {"base64": b64_img})

            if image_url:
                uploaded += 1
                html_parts.append(
                    f'<p><img src="{image_url}" alt="이미지 {uploaded}" style="max-width:100%;height:auto;"></p>'
                )
                print(f"   ✅ 이미지 업로드/삽입 완료: {size:,} bytes", flush=True)
                sys.stdout.flush()

        except Exception as e:
            print(f"   ⚠️  이미지 처리 실패: {e}", flush=True)
            sys.stdout.flush()

    if uploaded == 0:
        print("❌ [ERROR] 갤러리 게시판은 이미지가 필수인데, 유효 이미지가 0개입니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    final_content = "\n".join(html_parts) + f"\n<p><a href='{original_link}' target='_blank' rel='noopener'>📝 원문 보러가기</a></p>"

    print("📤 [5/5] 게시글 생성 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    req = {
        "shop_no": 1,
        "writer": "메디힐리",
        "title": title,
        "content": final_content,
        "client_ip": "127.0.0.1",
        "password": "1234"
    }

    payload = {"requests": [req]}

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"🔍 [DEBUG] 응답 코드: {res.status_code}", flush=True)
    print(f"🔍 [DEBUG] 응답: {res.text[:500]}", flush=True)
    sys.stdout.flush()

    if res.status_code == 201:
        print("\n" + "=" * 70, flush=True)
        print("🎉 게시글 업로드 성공! (헤딩/크기 변화 반영)", flush=True)
        print("=" * 70, flush=True)
        print(f"   📝 제목: {title}", flush=True)
        print(f"   🖼️  삽입 이미지: {uploaded}개", flush=True)
        print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/", flush=True)
        print("=" * 70, flush=True)
        sys.stdout.flush()
        return

    print("❌ [ERROR] 게시글 생성 실패", flush=True)
    print(res.text, flush=True)
    sys.stdout.flush()
    sys.exit(1)

# ============================================================================
# 메인 실행
# ============================================================================
def main():
    print("\n" + "=" * 70, flush=True)
    print("🚀 네이버 → 카페24 자동 포스팅 (블록/중복제거/헤딩 반영)", flush=True)
    print("=" * 70 + "\n", flush=True)
    sys.stdout.flush()

    required_vars = [MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]
    if not all(required_vars):
        print("❌ [ERROR] 환경 변수가 설정되지 않았습니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print("✅ 모든 필수 환경변수 확인 완료\n", flush=True)
    sys.stdout.flush()

    try:
        # 1) 토큰 갱신 (유지)
        access_token = refresh_and_save_token()

        # 2) 최신 글
        title, original_link, real_url = fetch_latest_post()

        # 3) 본문 블록 추출(순서 유지 + 중복 제거 + 병합)
        blocks, nav_headers = extract_blocks(real_url)

        # 4~5) 블록 순서대로 이미지 업로드 & 게시글 생성(헤딩 반영)
        upload_to_cafe24(access_token, title, blocks, original_link, nav_headers)

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
