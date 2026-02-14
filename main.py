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
# 🔐 [유지] 토큰 갱신 및 즉시 저장
# ============================================================================
def refresh_and_save_token():
    print("=" * 70, flush=True)
    print("🔐 [최우선] 토큰 갱신 및 저장 시작", flush=True)
    print("=" * 70, flush=True)
    sys.stdout.flush()

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
        res = requests.post(url, headers=headers, data=data, timeout=10)
        print(f"🔍 [DEBUG] 응답 상태 코드: {res.status_code}", flush=True)
        sys.stdout.flush()

        res.raise_for_status()
        token_data = res.json()

        access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')

        print("✅ [STEP 1] 토큰 발급 성공", flush=True)
        sys.stdout.flush()

        if not access_token or not new_refresh_token:
            print("❌ [FATAL] 토큰 발급 실패: 응답에 토큰이 없습니다.", flush=True)
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ [FATAL] 토큰 발급 요청 실패: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print("🔍 [STEP 2] GitHub Secrets 즉시 저장 시작", flush=True)
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
        print("✅ [STEP 2] GitHub Secrets 저장 성공!", flush=True)
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
    print("📡 [2/5] 네이버 블로그 최신 글 크롤링 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    rss_res = requests.get(RSS_URL, timeout=10)
    rss_res.raise_for_status()
    rss_root = ET.fromstring(rss_res.text)

    item = rss_root.find('.//item')
    if not item:
        print("❌ [ERROR] RSS에 게시글이 없습니다.", flush=True)
        sys.exit(1)

    post_title = (item.find('title').text or "").strip()
    post_link = (item.find('link').text or "").strip()

    print("✅ RSS 파싱 완료", flush=True)
    print(f"   제목: {post_title}", flush=True)
    sys.stdout.flush()

    path_part = post_link.split('/')[-1]
    log_no = path_part.split('?')[0]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"

    print("✅ [2/5] 최신 글 정보 수집 완료\n", flush=True)
    sys.stdout.flush()

    return post_title, post_link, real_url

# ============================================================================
# 텍스트 스타일: font-size 최대한 살리고 인라인으로 강제
# ============================================================================
def extract_font_px_from_tag(tag) -> int | None:
    max_px = None

    def pick(style_text: str):
        nonlocal max_px
        if not style_text:
            return
        for m in re.finditer(r"font-size\s*:\s*(\d+)\s*px", style_text, flags=re.I):
            px = int(m.group(1))
            if max_px is None or px > max_px:
                max_px = px

    pick(tag.get("style", ""))

    for s in tag.find_all(True, recursive=True):
        pick(s.get("style", ""))

    return max_px

def map_font_px(px: int | None, tag_name: str) -> dict:
    if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        base_px = 22 if tag_name in ["h1", "h2"] else 18
        px = px or base_px
        weight = 800 if tag_name in ["h1", "h2"] else 700
        mt, mb = 22, 12
    else:
        px = px or 16
        weight = 400
        mt, mb = 0, 14

    px = min(max(px, 13), 34)
    return {"px": px, "weight": weight, "mt": mt, "mb": mb, "lh": 1.7}

def safe_text_to_div(text: str, style: dict) -> str:
    safe = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
    )
    return (
        f'<div style="font-size:{style["px"]}px;'
        f'font-weight:{style["weight"]};'
        f'line-height:{style["lh"]};'
        f'margin:{style["mt"]}px 0 {style["mb"]}px 0;">'
        f'{safe}</div>'
    )

# ============================================================================
# ✅ 이미지 다운로드 핵심 수정: "원본 우선 + 업그레이드 폴백"
# ============================================================================
def set_query_param(url: str, key: str, value: str) -> str:
    try:
        p = urlparse(url)
        qs = parse_qs(p.query)
        qs[key] = [value]
        new_q = urlencode(qs, doseq=True)
        return urlunparse(p._replace(query=new_q))
    except Exception:
        return url

def try_download_image(url: str, headers: dict) -> bytes | None:
    """
    1) 원본 URL 그대로 시도
    2) 실패하면 type=w1200 / w2000 등 몇 개만 폴백 시도
    - 성공하면 bytes 반환
    """
    candidates = [url]

    # type 파라미터가 있거나, 붙여도 되는 케이스라면 폴백을 추가
    # (단, 폴백이 404 유발할 수 있으므로 '원본 우선'이 핵심)
    candidates.append(set_query_param(url, "type", "w1200"))
    candidates.append(set_query_param(url, "type", "w2000"))

    # 중복 제거
    uniq = []
    seen = set()
    for u in candidates:
        if u not in seen:
            uniq.append(u)
            seen.add(u)

    last_err = None
    for u in uniq:
        try:
            r = requests.get(u, headers=headers, timeout=15)
            if r.status_code == 200 and r.content and len(r.content) > 0:
                return r.content
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)

    return None

def pick_img_src(img_tag):
    # 네이버는 다양한 attribute에 원본이 숨겨져 있을 수 있음
    for k in ["data-original", "data-ori-src", "data-src", "data-lazy-src", "src"]:
        v = img_tag.get(k)
        if v:
            return v
    return None

# ============================================================================
# 3. 본문 블록(텍스트/이미지) 추출
# ============================================================================
def extract_blocks_and_images(real_url: str, max_images: int = 12):
    print("🧱 [3/5] 본문 블록(텍스트/이미지) 추출 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    headers = {"User-Agent": USER_AGENT}

    res = requests.get(real_url, headers=headers, timeout=15)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    content_area = soup.select_one(".se-main-container") or soup.select_one("#post-view")
    if not content_area:
        print("❌ [ERROR] 본문 영역을 찾지 못했습니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print("✅ 본문 영역 발견", flush=True)
    sys.stdout.flush()

    TEXT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"}
    blocks = []
    images = []
    img_count = 0

    candidates = content_area.find_all(["img", *list(TEXT_TAGS)], recursive=True)

    def is_nested_text_tag(tag):
        p = tag.parent
        while p is not None and getattr(p, "name", None):
            if p.name in TEXT_TAGS:
                return True
            p = p.parent
        return False

    seen_text = set()

    for el in candidates:
        # 이미지
        if el.name == "img":
            if img_count >= max_images:
                continue

            src = pick_img_src(el)
            if not src:
                continue
            if "postfiles.pstatic.net" not in src:
                continue

            img_bytes = try_download_image(src, headers=headers)
            if not img_bytes:
                print(f"   ⚠️  이미지 다운로드 실패(원본+폴백 모두 실패): {src}", flush=True)
                sys.stdout.flush()
                continue

            img_count += 1
            token = f"[[IMG_{img_count}]]"
            images.append({
                "token": token,
                "filename": f"image_{img_count}.jpg",
                "base64": base64.b64encode(img_bytes).decode(),
                "bytes": len(img_bytes),
                "src": src
            })
            blocks.append({"type": "image", "token": token})

            print(f"   ✅ 이미지 {img_count} 다운로드 성공 ({len(img_bytes):,} bytes)", flush=True)
            sys.stdout.flush()
            continue

        # 텍스트
        if el.name in TEXT_TAGS:
            if is_nested_text_tag(el):
                continue

            text = el.get_text(separator="\n", strip=True)
            if not text:
                continue

            # 중복 제거(한 번 더 안전장치)
            key = re.sub(r"\s+", " ", text.strip())
            if key in seen_text:
                continue
            seen_text.add(key)

            px = extract_font_px_from_tag(el)
            style = map_font_px(px, el.name)
            blocks.append({"type": "html", "html": safe_text_to_div(text, style)})

    print(f"✅ 블록 {len(blocks)}개 추출 완료 (이미지 {len(images)}개 포함)\n", flush=True)
    sys.stdout.flush()

    return blocks, images

# ============================================================================
# 4. 카페24 이미지 업로드 (성공 패턴 유지)
# ============================================================================
def upload_image_to_cafe24(access_token, image_data):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    payload = {"requests": [{"image": image_data["base64"]}]}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"      🔍 업로드 응답 코드: {res.status_code}", flush=True)
        sys.stdout.flush()

        if res.status_code in [200, 201]:
            result = res.json()
            image_url = None
            if "images" in result and isinstance(result["images"], list) and result["images"]:
                img_obj = result["images"][0]
                image_url = img_obj.get("path") or img_obj.get("url") or img_obj.get("image_url")
            elif "path" in result:
                image_url = result["path"]
            elif "url" in result:
                image_url = result["url"]

            if image_url:
                print(f"      ✅ 이미지 URL: {image_url}", flush=True)
                sys.stdout.flush()
                return image_url

            print(f"      ⚠️  URL 추출 실패: {json.dumps(result, ensure_ascii=False)[:400]}", flush=True)
            sys.stdout.flush()
            return None

        print(f"      ❌ 업로드 실패: {res.text[:300]}", flush=True)
        sys.stdout.flush()
        return None

    except Exception as e:
        print(f"      ❌ 업로드 에러: {e}", flush=True)
        sys.stdout.flush()
        return None

# ============================================================================
# 5. 게시글 생성
# ============================================================================
def upload_to_cafe24(access_token, title, blocks, original_link, images):
    print("📤 [4/5] 카페24 이미지 업로드 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    token_to_url = {}
    for idx, img in enumerate(images, 1):
        print(f"   🔄 이미지 {idx}/{len(images)} 업로드 중... (원본 {img.get('bytes',0):,} bytes)", flush=True)
        sys.stdout.flush()
        up = upload_image_to_cafe24(access_token, img)
        if up:
            token_to_url[img["token"]] = up

    print(f"✅ 이미지 업로드 완료 (성공 {len(token_to_url)}개)\n", flush=True)
    sys.stdout.flush()

    html_parts = []
    for b in blocks:
        if b["type"] == "html":
            html_parts.append(b["html"])
        elif b["type"] == "image":
            u = token_to_url.get(b["token"])
            if not u:
                continue
            html_parts.append(
                f'<div style="margin:14px 0;">'
                f'<img src="{u}" alt="image" style="max-width:100%; height:auto; display:block;">'
                f'</div>'
            )

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

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"🔍 [DEBUG] 응답 코드: {res.status_code}", flush=True)
    print(f"🔍 [DEBUG] 응답: {res.text[:800]}", flush=True)
    sys.stdout.flush()

    if res.status_code == 201:
        print("\n" + "=" * 70, flush=True)
        print("🎉 게시글 업로드 성공!", flush=True)
        print("=" * 70, flush=True)
        print(f"   📝 제목: {title}", flush=True)
        print(f"   🖼️  이미지 업로드 성공: {len(token_to_url)}개", flush=True)
        print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/", flush=True)
        print("=" * 70, flush=True)
        sys.stdout.flush()
        return

    print("❌ [ERROR] 게시글 생성 실패", flush=True)
    print(res.text, flush=True)
    sys.stdout.flush()
    sys.exit(1)

# ============================================================================
# main
# ============================================================================
def main():
    access_token = refresh_and_save_token()
    title, original_link, real_url = fetch_latest_post()

    blocks, images = extract_blocks_and_images(real_url, max_images=12)
    upload_to_cafe24(access_token, title, blocks, original_link, images)

    print("\n✅ 모든 작업 완료!\n", flush=True)
    sys.stdout.flush()

if __name__ == "__main__":
    print("\n🔍 [DEBUG] main() 함수 호출\n", flush=True)
    sys.stdout.flush()
    main()
