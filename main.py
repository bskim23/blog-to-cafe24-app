import os
import sys
import requests
import base64
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, Tag
from github import Github, Auth
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import json

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

# ✅ 이미지 품질 스크리닝 기준(바이트)
MIN_BYTES_ACCEPT = 80_000      # 이보다 작으면 저해상도 가능성 높음 → 업그레이드 강행
MIN_BYTES_KEEP = 25_000        # 이보다 작으면 업로드 자체를 스킵(엑박/썸네일급 방지)

print("=" * 70, flush=True)
print("🔍 [DEBUG] 스크립트 시작", flush=True)
print("=" * 70, flush=True)
sys.stdout.flush()

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

    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}

    res = requests.post(url, headers=headers, data=data, timeout=10)
    print(f"🔍 [DEBUG] 응답 상태 코드: {res.status_code}", flush=True)
    sys.stdout.flush()
    res.raise_for_status()

    token_data = res.json()
    access_token = token_data.get('access_token')
    new_refresh_token = token_data.get('refresh_token')

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

    item = rss_root.find('.//item')
    if not item:
        print("❌ [ERROR] RSS에 게시글이 없습니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    post_title = (item.find('title').text or "").strip()
    post_link = (item.find('link').text or "").strip()

    path_part = post_link.split('/')[-1]
    log_no = path_part.split('?')[0]
    real_url = f"https://blog.naver.com/PostView.naver?blogId=mediheally_lab&logNo={log_no}"

    print("✅ RSS 파싱 완료", flush=True)
    print(f"   제목: {post_title}", flush=True)
    print("✅ [2/5] 최신 글 정보 수집 완료\n", flush=True)
    sys.stdout.flush()

    return post_title, real_url

# ============================================================================
# 이미지 다운로드: 바이트 기준 최고 후보 채택
# ============================================================================
def pick_best_img_url(img_tag: Tag) -> str | None:
    for k in ["data-original", "data-ori-src", "data-src", "data-lazy-src", "src"]:
        v = img_tag.get(k)
        if v:
            return v
    return None

def set_type_param(url: str, type_value: str) -> str:
    try:
        p = urlparse(url)
        q = dict(parse_qsl(p.query, keep_blank_values=True))
        q["type"] = type_value
        new_q = urlencode(q, doseq=True)
        return urlunparse(p._replace(query=new_q))
    except Exception:
        return url

def strip_query(url: str) -> str:
    try:
        p = urlparse(url)
        return urlunparse(p._replace(query=""))
    except Exception:
        return url

def download_image(url: str, referer: str) -> bytes | None:
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": referer,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        if r.status_code == 200 and r.content:
            return r.content
        return None
    except Exception:
        return None

def download_best_image_by_size(base_url: str, referer: str, min_bytes_accept: int = MIN_BYTES_ACCEPT) -> tuple[bytes | None, str | None, int]:
    """
    base_url을 기준으로 여러 후보 URL에서 이미지를 받아보고,
    '가장 큰 파일'을 선택합니다.

    return: (best_bytes, best_url, best_size)
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

    # 중복 제거
    uniq = []
    seen = set()
    for u in candidates:
        if u and u not in seen:
            uniq.append(u)
            seen.add(u)

    best_bytes = None
    best_url = None
    best_size = 0

    for u in uniq:
        b = download_image(u, referer=referer)
        if not b:
            continue
        size = len(b)
        if size > best_size:
            best_bytes = b
            best_url = u
            best_size = size

        # 이미 충분히 큰 걸 잡았으면(기준 충족) 조기 종료
        if best_size >= min_bytes_accept and "w2000" in u:
            break

    return best_bytes, best_url, best_size

# ============================================================================
# 3. 본문 블록 추출(문단 기반) + 이미지 base64
# ============================================================================
def extract_blocks(real_url: str, max_images: int = 20):
    print("🧱 [3/5] 본문 블록(텍스트/이미지) 추출 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    headers = {"User-Agent": USER_AGENT}
    res = requests.get(real_url, headers=headers, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    content_area = soup.select_one(".se-main-container") or soup.select_one("#post-view")
    if not content_area:
        print("❌ [ERROR] 본문 영역을 찾지 못했습니다.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    print("✅ 본문 영역 발견", flush=True)
    sys.stdout.flush()

    blocks = []
    img_cnt = 0

    # 블록 태그 단위로만 순회 → 텍스트 조각화 방지
    for el in content_area.find_all(["p", "h1", "h2", "h3", "li", "blockquote", "img"], recursive=True):
        if el.name == "img":
            if img_cnt >= max_images:
                continue
            src = pick_best_img_url(el)
            if not src or "pstatic.net" not in src:
                continue

            best_bytes, best_url, best_size = download_best_image_by_size(src, referer=real_url)

            if not best_bytes:
                print(f"   ⚠️  이미지 다운로드 실패: {src}", flush=True)
                sys.stdout.flush()
                continue

            if best_size < MIN_BYTES_KEEP:
                # 너무 작은 건 업로드해봐야 썸네일 수준 → 스킵
                print(f"   ⚠️  이미지 스킵(너무 작음 {best_size:,} bytes): {best_url}", flush=True)
                sys.stdout.flush()
                continue

            img_cnt += 1
            blocks.append({
                "type": "image",
                "filename": f"image_{img_cnt}.jpg",
                "base64": base64.b64encode(best_bytes).decode(),
                "bytes": best_size,
                "picked_url": best_url
            })
            print(f"   ✅ 이미지 {img_cnt} 선택 ({best_size:,} bytes) | {best_url[:90]}...", flush=True)
            sys.stdout.flush()
            continue

        # 텍스트 블록
        txt = el.get_text(separator="\n", strip=True)
        if not txt:
            continue
        blocks.append({"type": "text", "text": txt, "tag": el.name})

    img_in_blocks = sum(1 for b in blocks if b["type"] == "image")
    print(f"✅ 블록 {len(blocks)}개 추출 완료 (이미지 {img_in_blocks}개 포함)\n", flush=True)
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
        print(f"      ❌ 업로드 실패: {res.status_code} {res.text[:200]}", flush=True)
        sys.stdout.flush()
        return None

    data = res.json()
    if "images" in data and data["images"]:
        return data["images"][0].get("path") or data["images"][0].get("url")
    return data.get("path") or data.get("url")

# ============================================================================
# 5. 게시글 생성: member_id로 관리자 노출 + attach_file_urls(썸네일)
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
        "member_id": MALL_ID,     # ✅ 메디** 방지(관리자 노출 유도)
        "title": title,
        "content": content_html,
        "client_ip": "127.0.0.1",
        # ✅ password 제거(비회원 글 느낌 제거)
    }

    if thumb_url:
        req["attach_file_urls"] = [{"name": "thumb.jpg", "url": thumb_url}]

    payload = {"requests": [req]}
    return requests.post(url, headers=headers, json=payload, timeout=30)

# ============================================================================
# 업로드 오케스트레이션
# ============================================================================
def upload_to_cafe24(access_token: str, title: str, blocks: list[dict]):
    print("📤 [4/5] 카페24 업로드 시작", flush=True)
    print("-" * 70, flush=True)
    sys.stdout.flush()

    html_parts = []
    first_image_url = None
    uploaded_images = 0

    # 전체 래퍼(텍스트 작고 이상한 문제 완화: 기본 폰트/라인고정)
    html_parts.append('<div style="font-size:16px; line-height:1.75; letter-spacing:-0.2px;">')

    for b in blocks:
        if b["type"] == "image":
            img_url = upload_image_to_cafe24(access_token, b)
            if img_url:
                uploaded_images += 1
                if not first_image_url:
                    first_image_url = img_url
                html_parts.append(
                    f'<p style="margin:14px 0;">'
                    f'<img src="{img_url}" alt="" style="max-width:100%;height:auto;display:block;">'
                    f'</p>'
                )
            continue

        # 텍스트: 문단 단위 렌더링
        txt = b["text"]
        lines = [x.strip() for x in txt.split("\n") if x.strip()]

        # 제목성 태그는 조금 강조(크기 조정은 "나중"이라 하셨으니 최소만)
        tag = b.get("tag", "p")
        if tag in ["h1", "h2", "h3"]:
            html_parts.append(f'<p style="margin:18px 0 10px 0; font-weight:700;">{lines[0]}</p>')
            for line in lines[1:]:
                html_parts.append(f'<p style="margin:0 0 12px 0;">{line}</p>')
        else:
            for line in lines:
                html_parts.append(f'<p style="margin:0 0 12px 0;">{line}</p>')

    html_parts.append("</div>")  # 래퍼 종료

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

    # ✅ 원본 보러가기 링크는 넣지 않음(요청사항)
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
    blocks = extract_blocks(real_url, max_images=20)
    upload_to_cafe24(access_token, title, blocks)
    print("\n✅ 모든 작업 완료!\n", flush=True)

if __name__ == "__main__":
    main()
