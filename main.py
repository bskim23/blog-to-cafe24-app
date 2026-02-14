import os
import sys
import re
import json
import base64
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from github import Github, Auth
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ============================================================================
# 🔐 [유지] 토큰 갱신 및 즉시 저장 (원본 구조 유지)
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

        post_title = (item.find('title').text or "").strip()
        post_link = (item.find('link').text or "").strip()

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
# 유틸: 네이버 이미지 URL을 가능한 고해상도로
# ============================================================================
def upgrade_naver_image_url(url: str, prefer_width: int = 1200) -> str:
    """
    네이버 블로그 이미지가 type=wNNN 형태로 리사이즈되는 경우가 많아서,
    가능한 큰 w값으로 업그레이드해서 다시 요청합니다.
    """
    if not url:
        return url

    try:
        # data: 같은 건 제외
        if url.startswith("data:"):
            return url

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        # type=w966 / w773 / w80_blur 같은 패턴이 흔함
        if "type" in qs and len(qs["type"]) > 0:
            t = qs["type"][0]
            # w숫자 또는 w숫자_...
            m = re.match(r"w(\d+)(.*)", t)
            if m:
                tail = m.group(2) or ""
                qs["type"] = [f"w{prefer_width}{tail}"]
                new_query = urlencode(qs, doseq=True)
                return urlunparse(parsed._replace(query=new_query))

        # query가 없거나 type이 없으면 그대로
        return url
    except Exception:
        return url

# ============================================================================
# 유틸: 폰트 사이즈 추출 및 맵핑
# ============================================================================
def extract_font_px_from_tag(tag) -> int | None:
    """
    태그 본인/하위 span 등의 style 속성에서 font-size: Npx 를 최대값으로 잡습니다.
    """
    max_px = None

    def pick_px(style_text: str):
        nonlocal max_px
        if not style_text:
            return
        for m in re.finditer(r"font-size\s*:\s*(\d+)\s*px", style_text, flags=re.I):
            px = int(m.group(1))
            if (max_px is None) or (px > max_px):
                max_px = px

    # 본인 style
    pick_px(tag.get("style", ""))

    # 하위 span/style
    for s in tag.find_all(True, recursive=True):
        pick_px(s.get("style", ""))

    return max_px

def map_font_px(px: int | None, tag_name: str) -> dict:
    """
    px가 없으면 태그 성격(제목/본문)에 따라 기본값을 줌
    """
    # 기본
    if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        base_px = 22 if tag_name in ["h1", "h2"] else 18
        px = px or base_px
        weight = 800 if tag_name in ["h1", "h2"] else 700
        margin_top = 22
        margin_bottom = 12
    else:
        px = px or 16
        weight = 400
        margin_top = 0
        margin_bottom = 14

    # 과도한 값 클램프(스킨에서 너무 튈 수 있어 상한만)
    if px > 34:
        px = 34
    if px < 13:
        px = 13

    return {
        "px": px,
        "weight": weight,
        "mt": margin_top,
        "mb": margin_bottom,
        "lh": 1.7
    }

# ============================================================================
# 3. 본문을 "블록(텍스트/이미지)" 순서대로 추출 + 이미지 base64
# ============================================================================
def extract_blocks_and_images(real_url: str, max_images: int = 12):
    """
    핵심(A):
    - 이미지/텍스트를 '원본 등장 순서대로' 블록화
    - 텍스트는 get_text로 뭉개지지 않게, 최소한의 줄바꿈을 <br>로 보존
    - 폰트 크기는 style에서 최대한 읽어서 인라인 스타일로 박아둠
    - 이미지는 가능한 고해상도(type=w1200)로 재요청
    """
    print("🧱 [3/5] 본문 블록(텍스트/이미지) 추출 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    headers = {"User-Agent": USER_AGENT}

    try:
        res = requests.get(real_url, headers=headers, timeout=15)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        # 스마트에디터/구형 스킨 대응
        content_area = soup.select_one(".se-main-container") or soup.select_one("#post-view")
        if not content_area:
            print("❌ [ERROR] 본문 영역을 찾지 못했습니다.", flush=True)
            sys.exit(1)

        print("✅ 본문 영역 발견", flush=True)
        sys.stdout.flush()

        # 문서 순서대로 텍스트/이미지 후보를 수집
        # - 중첩된 p 안의 span 등은 p 단위로만 처리
        TEXT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"}
        blocks = []
        images = []
        img_count = 0

        # 모든 후보를 "문서 순서대로"
        candidates = content_area.find_all(["img", *list(TEXT_TAGS)], recursive=True)

        def is_nested_text_tag(tag):
            # tag가 TEXT_TAGS인데, 상위에 또 TEXT_TAGS가 있으면 중복 방지
            p = tag.parent
            while p is not None and getattr(p, "name", None):
                if p.name in TEXT_TAGS:
                    return True
                p = p.parent
            return False

        for el in candidates:
            # 이미지
            if el.name == "img":
                if img_count >= max_images:
                    continue

                src = el.get("data-src") or el.get("data-lazy-src") or el.get("src") or ""
                if "postfiles.pstatic.net" not in src:
                    continue

                hi_url = upgrade_naver_image_url(src, prefer_width=1200)

                try:
                    img_res = requests.get(hi_url, headers=headers, timeout=15)
                    img_res.raise_for_status()

                    b64_img = base64.b64encode(img_res.content).decode()
                    img_count += 1

                    token = f"[[IMG_{img_count}]]"
                    images.append({
                        "token": token,
                        "filename": f"image_{img_count}.jpg",
                        "base64": b64_img,
                        "bytes": len(img_res.content),
                        "src": hi_url
                    })

                    blocks.append({"type": "image", "token": token})

                    print(f"   ✅ 이미지 {img_count} 다운로드 ({len(img_res.content):,} bytes) | {hi_url[:90]}...", flush=True)
                    sys.stdout.flush()

                except Exception as e:
                    print(f"   ⚠️  이미지 다운로드 실패: {e}", flush=True)
                    sys.stdout.flush()

                continue

            # 텍스트
            if el.name in TEXT_TAGS:
                if is_nested_text_tag(el):
                    continue

                text = el.get_text(separator="\n", strip=True)
                if not text:
                    continue

                # 원본 폰트 크기 최대한 추출
                px = extract_font_px_from_tag(el)
                style = map_font_px(px, el.name)

                # 줄바꿈 보존
                safe_html = (
                    text.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace("\n", "<br>")
                )

                # 제목 성격이면 약간 더 타이트하게
                if el.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    html = (
                        f'<div style="font-size:{style["px"]}px;'
                        f'font-weight:{style["weight"]};'
                        f'line-height:{style["lh"]};'
                        f'margin:{style["mt"]}px 0 {style["mb"]}px 0;">'
                        f'{safe_html}</div>'
                    )
                else:
                    html = (
                        f'<div style="font-size:{style["px"]}px;'
                        f'font-weight:{style["weight"]};'
                        f'line-height:{style["lh"]};'
                        f'margin:{style["mt"]}px 0 {style["mb"]}px 0;">'
                        f'{safe_html}</div>'
                    )

                blocks.append({"type": "html", "html": html})

        if not blocks:
            print("❌ [ERROR] 블록 추출 결과가 비었습니다.", flush=True)
            sys.exit(1)

        print(f"✅ 블록 {len(blocks)}개 추출 완료 (이미지 {len(images)}개 포함)\n", flush=True)
        sys.stdout.flush()

        return blocks, images

    except Exception as e:
        print(f"❌ [ERROR] 본문 추출 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 4. 이미지를 카페24 Products Images API로 업로드 (현재 성공 패턴 유지)
# ============================================================================
def upload_image_to_cafe24(access_token, image_data):
    """
    카페24 Products Images API로 이미지 업로드 → 이미지 URL 받기
    (성공했던 requests[].image 패턴 유지)
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

    print(f"      🔍 Payload 구조: requests[].image", flush=True)
    sys.stdout.flush()

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"      🔍 업로드 응답 코드: {res.status_code}", flush=True)
        sys.stdout.flush()

        if res.status_code in [200, 201]:
            result = res.json()

            image_url = None
            if "images" in result and isinstance(result["images"], list) and len(result["images"]) > 0:
                img_obj = result["images"][0]
                image_url = img_obj.get("path") or img_obj.get("url") or img_obj.get("image_url")
            elif "image" in result:
                if isinstance(result["image"], dict):
                    image_url = result["image"].get("path") or result["image"].get("url")
                elif isinstance(result["image"], str):
                    image_url = result["image"]
            elif "path" in result:
                image_url = result["path"]
            elif "url" in result:
                image_url = result["url"]

            if image_url:
                print(f"      ✅ 이미지 URL: {image_url}", flush=True)
                sys.stdout.flush()
                return image_url

            print("      ⚠️  URL 추출 실패(응답 구조 확인 필요)", flush=True)
            print(json.dumps(result, ensure_ascii=False, indent=2)[:800], flush=True)
            sys.stdout.flush()
            return None

        print(f"      ❌ 업로드 실패: {res.text[:400]}", flush=True)
        sys.stdout.flush()
        return None

    except Exception as e:
        print(f"      ❌ 에러: {e}", flush=True)
        sys.stdout.flush()
        return None

# ============================================================================
# 5. 카페24 게시글 생성: 블록을 섞어 final_content 구성
# ============================================================================
def upload_to_cafe24(access_token, title, blocks, original_link, images):
    """
    핵심(A):
    - blocks(텍스트/이미지 순서)를 그대로 final_content로 직렬화
    - 이미지 token을 업로드된 URL로 치환
    - 글씨 크기는 인라인 스타일로 박혀서 스킨 영향 최소화
    """
    print("📤 [4/5] 카페24 이미지 업로드 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    if not images:
        print("❌ [ERROR] 이미지가 0개입니다. (갤러리/콘텐츠 품질상 최소 1개 권장)", flush=True)
        sys.stdout.flush()

    # 1) 이미지 업로드 → token:url 맵 생성
    token_to_url = {}
    for idx, img_data in enumerate(images, 1):
        print(f"   🔄 이미지 {idx}/{len(images)} 업로드 중... (원본 {img_data.get('bytes', 0):,} bytes)", flush=True)
        sys.stdout.flush()

        up_url = upload_image_to_cafe24(access_token, img_data)
        if up_url:
            token_to_url[img_data["token"]] = up_url

    if images and not token_to_url:
        print("❌ [ERROR] 모든 이미지 업로드 실패", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print(f"✅ 이미지 업로드 완료 (성공 {len(token_to_url)}개)\n", flush=True)
    sys.stdout.flush()

    # 2) blocks를 순서대로 HTML로 직렬화
    html_parts = []
    for b in blocks:
        if b["type"] == "html":
            html_parts.append(b["html"])
        elif b["type"] == "image":
            tok = b["token"]
            img_url = token_to_url.get(tok)
            if not img_url:
                # 업로드 실패한 이미지는 건너뛰되, 흐름은 유지(공백)
                continue
            html_parts.append(
                f'<div style="margin:14px 0;">'
                f'<img src="{img_url}" alt="image" style="max-width:100%; height:auto; display:block;">'
                f'</div>'
            )

    # 3) 원문 링크/하단 고정
    html_parts.append(
        f'<div style="margin:26px 0 0 0; font-size:14px; line-height:1.6;">'
        f'<a href="{original_link}" target="_blank" rel="noopener noreferrer">📝 원문 보러가기</a>'
        f'</div>'
    )

    final_content = "\n".join(html_parts)

    print("📤 [5/5] 게시글 생성 시작", flush=True)
    print("-" * 70, flush=True)
    print(f"🔍 [DEBUG] final_content 길이: {len(final_content):,} chars", flush=True)
    sys.stdout.flush()

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }

    # 게시글 생성 API: writer/title/content/client_ip 등이 필수  [oai_citation:1‡partners.cafe24.com](https://partners.cafe24.com/docs/en/api/admin/)
    payload = {
        "requests": [
            {
                "shop_no": 1,
                "writer": "메디힐리",
                "title": title,
                "content": final_content,
                "client_ip": "127.0.0.1",
                "password": "1234"
            }
        ]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"\n🔍 [DEBUG] 응답 코드: {res.status_code}", flush=True)
        print(f"🔍 [DEBUG] 응답: {res.text[:800]}", flush=True)
        sys.stdout.flush()

        if res.status_code == 201:
            print("\n" + "=" * 70, flush=True)
            print("🎉 게시글 업로드 성공!", flush=True)
            print("=" * 70, flush=True)
            print(f"   📝 제목: {title}", flush=True)
            print(f"   ✍️  작성자: 메디힐리", flush=True)
            print(f"   🖼️  이미지 업로드 성공: {len(token_to_url)}개", flush=True)
            print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/", flush=True)
            print("=" * 70, flush=True)
            sys.stdout.flush()
            return

        print(f"\n❌ [ERROR] 게시글 생성 실패 (HTTP {res.status_code})", flush=True)
        print(f"   전체 응답: {res.text}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    except Exception as e:
        print(f"❌ [ERROR] 게시글 생성 에러: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# 메인 실행
# ============================================================================
def main():
    print("\n" + "=" * 70, flush=True)
    print("🚀 네이버 → 카페24 자동 포스팅 (A: 흐름/서식 개선 버전)", flush=True)
    print("=" * 70 + "\n", flush=True)
    sys.stdout.flush()

    required_vars = [MALL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]
    if not all(required_vars):
        print("❌ [ERROR] 환경 변수가 설정되지 않았습니다.", flush=True)
        sys.exit(1)

    print("✅ 모든 필수 환경변수 확인 완료\n", flush=True)
    sys.stdout.flush()

    # 1) 토큰 갱신/저장 (유지)
    access_token = refresh_and_save_token()

    # 2) 최신 글
    title, original_link, real_url = fetch_latest_post()

    # 3) 블록(텍스트/이미지) 추출 (순서 유지 + font-size 최대한 반영)
    blocks, images = extract_blocks_and_images(real_url, max_images=12)

    # 4~5) 이미지 업로드 → 블록을 섞어 게시글 생성
    upload_to_cafe24(access_token, title, blocks, original_link, images)

    print("\n✅ 모든 작업 완료!\n", flush=True)
    sys.stdout.flush()

# ============================================================================
# 진입점
# ============================================================================
if __name__ == "__main__":
    print("\n🔍 [DEBUG] main() 함수 호출\n", flush=True)
    sys.stdout.flush()
    main()
