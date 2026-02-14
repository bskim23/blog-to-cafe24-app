import os
import sys
import re
import json
import base64
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, Tag
from github import Github, Auth
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

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
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ✅ 이미지 품질 스크리닝(바이트)
MIN_BYTES_ACCEPT = 80_000   # 이 이상이면 충분히 본문용 가능성이 높음
MIN_BYTES_KEEP = 25_000     # 이 이하면 업로드 스킵(스티커/아이콘급 방지)
MAX_IMAGES = 30

print("=" * 70, flush=True)
print("🔍 [DEBUG] 스크립트 시작", flush=True)
print("=" * 70, flush=True)
sys.stdout.flush()

# ============================================================================
# 🔐 토큰 갱신 및 즉시 저장 (유지)
# ============================================================================
def refresh_and_save_token():
    print("=" * 70, flush=True)
    print("🔐 [최우선] 토큰 갱신 및 저장 시작", flush=True)
    print("=" * 70, flush=True)
    sys.stdout.flush()

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()

    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}

    res = requests.post(url, headers=headers, data=data, timeout=10)
    print(f"🔍 [DEBUG] 응답 상태 코드: {res.status_code}", flush=True)
    sys.stdout.flush()
    res.raise_for_status()

    token_data = res.json()
    access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token")

    if not access_token or not new_refresh_token:
        print("❌ [FATAL] 토큰 발급 실패: 응답에 토큰이 없습니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print("✅ [STEP 1] 토큰 발급 성공", flush=True)
    sys.stdout.flush()

    print("🔍 [STEP 2] GitHub Secrets 즉시 저장 시작", flush=True)
    sys.stdout.flush()

    if PA_TOKEN and GITHUB_REPO:
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
# 2. 네이버 RSS 최신 글
# ============================================================================
def fetch_latest_post():
    print("📡 [2/5] 네이버 블로그 최신 글 크롤링 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    rss_res = requests.get(RSS_URL, timeout=10)
    rss_res.raise_for_status()
    rss_root = ET.fromstring(rss_res.text)

    item = rss_root.find(".//item")
    if not item:
        print("❌ [ERROR] RSS에 게시글이 없습니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    post_title = (item.find("title").text or "").strip()
    post_link = (item.find("link").text or "").strip()

    path_part = post_link.split("/")[-1]
    log_no = path_part.split("?")[0]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"

    print("✅ RSS 파싱 완료", flush=True)
    print(f"   제목: {post_title}", flush=True)
    print("✅ [2/5] 최신 글 정보 수집 완료\n", flush=True)
    sys.stdout.flush()

    return post_title, real_url

# ============================================================================
# 이미지 다운로드: 후보 여러 개 받고 "가장 큰 bytes" 선택 + 진짜 이미지 검사
# ============================================================================
def set_type_param(url: str, type_value: str) -> str:
    try:
        p = urlparse(url)
        q = dict(parse_qsl(p.query, keep_blank_values=True))
        q["type"] = type_value
        return urlunparse(p._replace(query=urlencode(q, doseq=True)))
    except Exception:
        return url

def strip_query(url: str) -> str:
    try:
        p = urlparse(url)
        return urlunparse(p._replace(query=""))
    except Exception:
        return url

def is_probably_image_bytes(b: bytes) -> bool:
    if not b or len(b) < 32:
        return False
    head = b[:16]
    # JPEG/PNG/GIF/WEBP
    if head.startswith(b"\xff\xd8\xff"):
        return True
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return True
    if head.startswith(b"RIFF") and b"WEBP" in b[:16]:
        return True
    # HTML 에러페이지 방지
    if b[:200].lstrip().lower().startswith(b"<!doctype html") or b[:200].lstrip().lower().startswith(b"<html"):
        return False
    return True

def download_image(url: str, referer: str) -> tuple[bytes | None, str | None]:
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": referer,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
        if r.status_code != 200 or not r.content:
            return None, None
        # content-type도 같이 참고
        ctype = (r.headers.get("Content-Type") or "").lower()
        b = r.content
        if ("image/" in ctype) or is_probably_image_bytes(b):
            return b, ctype
        return None, None
    except Exception:
        return None, None

def download_best_image_by_size(base_url: str, referer: str) -> tuple[bytes | None, str | None, int]:
    """
    - 후보 URL을 여럿 시도
    - 성공한 것 중 bytes가 가장 큰 것 선택
    """
    if not base_url:
        return None, None, 0

    candidates = [
        base_url,
        set_type_param(base_url, "w2000"),
        set_type_param(base_url, "w1200"),
        set_type_param(base_url, "w966"),
        strip_query(base_url),
    ]

    uniq = []
    seen = set()
    for u in candidates:
        if u and u not in seen:
            uniq.append(u)
            seen.add(u)

    best_b, best_u, best_sz = None, None, 0

    for u in uniq:
        b, _ctype = download_image(u, referer=referer)
        if not b:
            continue
        sz = len(b)
        if sz > best_sz:
            best_b, best_u, best_sz = b, u, sz

        # 충분히 큰 이미지면 조기 종료
        if best_sz >= MIN_BYTES_ACCEPT and ("w2000" in u or "w1200" in u):
            break

    return best_b, best_u, best_sz

def pick_img_url_from_tag(img_tag: Tag) -> str | None:
    # 원본이 숨겨져 있는 경우 우선순위
    for k in ["data-original", "data-ori-src", "data-src", "data-lazy-src", "src"]:
        v = img_tag.get(k)
        if v:
            return v
    return None

# ============================================================================
# 네이버 "외부 링크/OG 카드" 이미지 스킵 규칙
# ============================================================================
def is_link_card_component(comp: Tag) -> bool:
    """
    네이버에서 본문 하단(혹은 중간)에 '별도 링크로 넘어가는 카드' 컴포넌트는
    대표적으로 se-oglink / se-link / se-section-oglink 류 클래스/데이터를 가짐.
    """
    cls = " ".join(comp.get("class", [])).lower()
    if "oglink" in cls or "se-oglink" in cls or "se-link" in cls:
        return True
    # data-linkdata / data-link 같은 속성도 카드류 단서
    for attr in ["data-linkdata", "data-link", "data-linktype", "data-oglink"]:
        if comp.has_attr(attr):
            return True
    # 내부에 a태그가 있고, 카드 구조로 보이면 제외(보수적으로)
    if comp.find("a") and comp.find(class_=re.compile(r"oglink|se-oglink|se-link", re.I)):
        return True
    return False

# ============================================================================
# 3. 본문을 "컴포넌트 단위"로 순회하여 (순서 보존/중복 제거)
# ============================================================================
def extract_blocks_from_naver(real_url: str) -> list[dict]:
    print("🧱 [3/5] 본문 블록(텍스트/이미지) 추출 시작 (컴포넌트 단위)", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    res = requests.get(real_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    content_area = soup.select_one(".se-main-container") or soup.select_one("#post-view")
    if not content_area:
        print("❌ [ERROR] 본문 영역을 찾지 못했습니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print("✅ 본문 영역 발견", flush=True)
    sys.stdout.flush()

    # ✅ 핵심: se-component를 문서 순서대로
    components = content_area.select("div.se-component")
    blocks: list[dict] = []
    img_cnt = 0

    prev_text_key = None  # 연속 중복 제거(강력)
    seen_text_keys = set()  # 전역 중복도 한번 더 방지

    for comp in components:
        # 1) 링크 카드 컴포넌트는 통째로 스킵
        if is_link_card_component(comp):
            continue

        cls = " ".join(comp.get("class", [])).lower()

        # 2) 이미지 컴포넌트
        # (se-image, se-component-image 등 다양한 변형이 있으니 img 태그 존재로 판단)
        img_tag = comp.find("img")
        if img_tag and ("pstatic.net" in (pick_img_url_from_tag(img_tag) or "")):
            if img_cnt >= MAX_IMAGES:
                continue

            src = pick_img_url_from_tag(img_tag)
            best_b, best_u, best_sz = download_best_image_by_size(src, referer=real_url)
            if not best_b:
                print(f"   ⚠️  이미지 다운로드 실패: {src}", flush=True)
                sys.stdout.flush()
                continue
            if best_sz < MIN_BYTES_KEEP:
                print(f"   ⚠️  이미지 스킵(너무 작음 {best_sz:,} bytes): {best_u}", flush=True)
                sys.stdout.flush()
                continue

            img_cnt += 1
            blocks.append({
                "type": "image",
                "filename": f"image_{img_cnt}.jpg",
                "base64": base64.b64encode(best_b).decode(),
                "bytes": best_sz,
                "picked_url": best_u
            })
            print(f"   ✅ 이미지 {img_cnt} 선택 ({best_sz:,} bytes)", flush=True)
            sys.stdout.flush()
            continue

        # 3) 텍스트 컴포넌트: 컴포넌트당 1회만 추출(중복 방지 핵심)
        text = comp.get_text(separator="\n", strip=True)
        if text:
            # 공백 정규화로 중복 키 생성
            key = re.sub(r"\s+", " ", text).strip()

            # (a) 바로 직전과 동일하면 제거
            if prev_text_key == key:
                continue
            # (b) 글 전체에서 동일 텍스트가 반복되면 제거(심각하다고 하셔서 강하게)
            if key in seen_text_keys:
                continue

            prev_text_key = key
            seen_text_keys.add(key)

            blocks.append({"type": "text", "text": text})

    print(f"✅ 블록 {len(blocks)}개 추출 완료 (이미지 {img_cnt}개 포함)\n", flush=True)
    sys.stdout.flush()

    return blocks

# ============================================================================
# 4. 카페24 Products Images 업로드
# ============================================================================
def upload_image_to_cafe24(access_token: str, image_data: dict) -> str | None:
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }
    payload = {"requests": [{"image": image_data["base64"]}]}

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    if res.status_code not in [200, 201]:
        print(f"      ❌ 업로드 실패: {res.status_code} {res.text[:250]}", flush=True)
        sys.stdout.flush()
        return None

    data = res.json()
    if "images" in data and data["images"]:
        return data["images"][0].get("path") or data["images"][0].get("url")
    return data.get("path") or data.get("url")

# ============================================================================
# 5. 게시글 생성: member_id로 관리자 노출 + 썸네일 attach_file_urls
# ============================================================================
def create_board_article(access_token: str, title: str, content_html: str, thumb_url: str | None):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{BOARD_NO}/articles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"
    }

    req = {
        "shop_no": 1,
        "writer": "관리자",
        "member_id": MALL_ID,   # ✅ 비회원/메디** 방지
        "title": title,
        "content": content_html,
        "client_ip": "127.0.0.1",
        # ✅ password 없음
        # ✅ 원본 보러가기 링크 없음
    }

    if thumb_url:
        req["attach_file_urls"] = [{"name": "thumb.jpg", "url": thumb_url}]

    payload = {"requests": [req]}
    return requests.post(url, headers=headers, json=payload, timeout=30)

# ============================================================================
# 오케스트레이션: 순서 그대로 HTML 조립
# ============================================================================
def upload_to_cafe24(access_token: str, title: str, blocks: list[dict]):
    print("📤 [4/5] 카페24 업로드 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    html_parts = []
    first_image_url = None
    uploaded_images = 0

    # 텍스트가 작고 이상한 문제 완화(기본 래퍼)
    html_parts.append('<div style="font-size:16px; line-height:1.75; letter-spacing:-0.2px;">')

    for b in blocks:
        if b["type"] == "image":
            img_url = upload_image_to_cafe24(access_token, b)
            if not img_url:
                continue
            uploaded_images += 1
            if not first_image_url:
                first_image_url = img_url
            html_parts.append(
                '<div style="margin:14px 0;">'
                f'<img src="{img_url}" alt="" style="max-width:100%; height:auto; display:block;">'
                "</div>"
            )
        else:
            # 문단 단위로 출력
            lines = [x.strip() for x in b["text"].split("\n") if x.strip()]
            for line in lines:
                html_parts.append(f'<p style="margin:0 0 12px 0;">{line}</p>')

    html_parts.append("</div>")

    if uploaded_images == 0:
        print("❌ [ERROR] 이미지가 0개입니다. (갤러리 품질상 최소 1개 권장)", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    content_html = "\n".join(html_parts)

    print(f"✅ 이미지 업로드 완료: {uploaded_images}개", flush=True)
    sys.stdout.flush()

    print("📤 [5/5] 게시글 생성 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    res = create_board_article(access_token, title, content_html, first_image_url)

    print(f"응답 코드: {res.status_code}", flush=True)
    print(f"응답 본문: {res.text[:500]}", flush=True)
    sys.stdout.flush()

    if res.status_code == 201:
        print("=" * 70, flush=True)
        print("🎉 게시글 업로드 성공!", flush=True)
        print("=" * 70, flush=True)
        print(f"🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/", flush=True)
        sys.stdout.flush()
    else:
        print("❌ [ERROR] 게시글 생성 실패", flush=True)
        sys.stdout.flush()
        sys.exit(1)

# ============================================================================
# main
# ============================================================================
def main():
    access_token = refresh_and_save_token()
    title, real_url = fetch_latest_post()

    blocks = extract_blocks_from_naver(real_url)
    upload_to_cafe24(access_token, title, blocks)

    print("\n✅ 모든 작업 완료!\n", flush=True)
    sys.stdout.flush()

if __name__ == "__main__":
    main()
