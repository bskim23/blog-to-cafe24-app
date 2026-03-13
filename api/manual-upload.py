from http.server import BaseHTTPRequestHandler
import os
import re
import json
import base64
import requests
from bs4 import BeautifulSoup


# ============================================================================
# 설정
# ============================================================================
MALL_ID = os.environ.get("CAFE24_MALL_ID")
CLIENT_ID = os.environ.get("CAFE24_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CAFE24_CLIENT_SECRET")
BOOTSTRAP_REFRESH_TOKEN = os.environ.get("CAFE24_REFRESH_TOKEN")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

MIN_BYTES_KEEP = 25_000
BASE_FONT_SIZE = 19
API_VERSION = "2025-12-01"


# ============================================================================
# 디버그 보조
# ============================================================================
def mask_value(value):
    if not value:
        return {"present": False, "length": 0, "tail": ""}
    text = str(value)
    return {
        "present": True,
        "length": len(text),
        "tail": text[-4:] if len(text) >= 4 else text,
    }


def get_env_debug():
    return {
        "CAFE24_MALL_ID": mask_value(MALL_ID),
        "CAFE24_CLIENT_ID": mask_value(CLIENT_ID),
        "CAFE24_CLIENT_SECRET": mask_value(CLIENT_SECRET),
        "CAFE24_REFRESH_TOKEN": mask_value(BOOTSTRAP_REFRESH_TOKEN),
        "SUPABASE_URL": mask_value(SUPABASE_URL),
        "SUPABASE_SERVICE_ROLE_KEY": mask_value(SUPABASE_SERVICE_ROLE_KEY),
    }


def safe_json_or_text(res):
    try:
        return res.json()
    except Exception:
        return res.text


# ============================================================================
# 환경변수 체크
# ============================================================================
def validate_env():
    required = {
        "CAFE24_MALL_ID": MALL_ID,
        "CAFE24_CLIENT_ID": CLIENT_ID,
        "CAFE24_CLIENT_SECRET": CLIENT_SECRET,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(
            json.dumps(
                {
                    "message": f"필수 환경변수가 없습니다: {', '.join(missing)}",
                    "env_debug": get_env_debug(),
                },
                ensure_ascii=False,
            )
        )


# ============================================================================
# Supabase refresh token 저장소
# ============================================================================
def supabase_headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def load_refresh_token():
    validate_env()

    url = (
        f"{SUPABASE_URL}/rest/v1/app_secrets"
        f"?key=eq.cafe24_refresh_token&select=value"
    )
    res = requests.get(url, headers=supabase_headers(), timeout=15)
    res.raise_for_status()

    data = res.json()
    if data and isinstance(data, list) and len(data) > 0:
        token = data[0].get("value")
        if token:
            return token, "supabase"

    if BOOTSTRAP_REFRESH_TOKEN:
        return BOOTSTRAP_REFRESH_TOKEN, "vercel_env"

    raise ValueError(
        json.dumps(
            {
                "message": "사용 가능한 refresh token이 없습니다.",
                "env_debug": get_env_debug(),
                "token_source": "none",
            },
            ensure_ascii=False,
        )
    )


def save_refresh_token(new_token):
    if not new_token:
        return

    url = f"{SUPABASE_URL}/rest/v1/app_secrets"
    payload = {
        "key": "cafe24_refresh_token",
        "value": new_token,
    }

    headers = supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()


# ============================================================================
# 카페24 토큰 갱신
# ============================================================================
def refresh_access_token():
    refresh_token, token_source = load_refresh_token()

    url = f"https://{MALL_ID}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()

    res = requests.post(
        url,
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=20,
    )

    if res.status_code >= 400:
        raise requests.HTTPError(
            json.dumps(
                {
                    "message": "카페24 토큰 재발급 실패",
                    "status_code": res.status_code,
                    "token_source": token_source,
                    "env_debug": get_env_debug(),
                    "cafe24_response": safe_json_or_text(res),
                },
                ensure_ascii=False,
            ),
            response=res,
        )

    data = res.json()
    access_token = data.get("access_token")
    if not access_token:
        raise ValueError(
            json.dumps(
                {
                    "message": "카페24 access_token을 받지 못했습니다.",
                    "token_source": token_source,
                    "env_debug": get_env_debug(),
                    "token_response_keys": list(data.keys()),
                },
                ensure_ascii=False,
            )
        )

    rotated_refresh_token = data.get("refresh_token")
    if rotated_refresh_token and rotated_refresh_token != refresh_token:
        save_refresh_token(rotated_refresh_token)

    return access_token


# ============================================================================
# 네이버 URL 정규화
# ============================================================================
def normalize_naver_url(url):
    url = url.strip()
    if not url:
        raise ValueError("블로그 주소가 비어 있습니다.")

    if "PostList.naver" in url:
        raise ValueError("목록 페이지 주소입니다. 개별 포스팅 상세 주소를 입력해 주세요.")

    url = url.replace("m.blog.naver.com", "blog.naver.com")

    patterns = [
        r"blog\.naver\.com/([^/]+)/([0-9]+)",
        r"PostView\.naver\?blogId=([^&]+)&logNo=([0-9]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            blog_id = match.group(1)
            log_no = match.group(2)
            return f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

    raise ValueError("네이버 블로그 글 주소 형식을 인식하지 못했습니다.")


# ============================================================================
# 제목 추출
# ============================================================================
def extract_title(real_url):
    res = requests.get(real_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    title_el = soup.select_one(".se-title-text span") or soup.select_one(".pcol1 .title")
    if not title_el:
        raise ValueError("제목을 찾지 못했습니다.")

    return title_el.get_text(strip=True)


# ============================================================================
# 원본 이미지 처리 + 디버그
# ============================================================================
def download_image_as_b64(url, referer, debug_item):
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": referer,
    }

    try:
        original_url = url
        if "pstatic.net" in url:
            url = url.split("?")[0] + "?type=w2000"

        debug_item["download_original_url"] = original_url
        debug_item["download_final_url"] = url

        r = requests.get(url, headers=headers, timeout=20)
        debug_item["download_status"] = r.status_code
        debug_item["download_bytes"] = len(r.content)

        if r.status_code == 200 and len(r.content) > MIN_BYTES_KEEP:
            debug_item["passed_size_filter"] = True
            return base64.b64encode(r.content).decode()

        debug_item["passed_size_filter"] = False
        return None

    except Exception as e:
        debug_item["download_exception"] = str(e)
        return None


def upload_to_cafe24_img(access_token, b64, debug_item):
    url = f"https://{MALL_ID}.cafe24api.com/api/v2/admin/products/images"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": API_VERSION,
    }
    payload = {"requests": [{"image": b64}]}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        debug_item["upload_status"] = res.status_code
        debug_item["upload_response"] = safe_json_or_text(res)

        if res.status_code in [200, 201]:
            image_url = res.json()["images"][0].get("url")
            debug_item["uploaded_url"] = image_url
            return image_url

        return None
    except Exception as e:
        debug_item["upload_exception"] = str(e)
        return None


# ============================================================================
# 원본 본문 조립 + 디버그
# ============================================================================
def build_final_content(access_token, real_url):
    res = requests.get(real_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    content_area = soup.select_one(".se-main-container")

    if not content_area:
        raise ValueError("본문 영역을 찾지 못했습니다. 비공개 글이거나 구조가 다를 수 있습니다.")

    html_parts = [
        f'<div style="font-size:{BASE_FONT_SIZE}px; line-height:1.8; color:#333; word-break:keep-all;">'
    ]
    first_img_url = None
    seen = set()
    image_debug = []

    for el in content_area.find_all(recursive=True):
        if el in seen:
            continue

        is_img_comp = "se-image" in el.get("class", []) or el.name == "img"

        if is_img_comp and el.name != "div":
            img_tag = el if el.name == "img" else el.find("img")

            if img_tag:
                src = img_tag.get("data-src") or img_tag.get("src")
                debug_item = {
                    "element_name": el.name,
                    "element_classes": el.get("class", []),
                    "src": src,
                }

                if src and not src.endswith(".svg"):
                    b64 = download_image_as_b64(src, real_url, debug_item)

                    if b64:
                        up_url = upload_to_cafe24_img(access_token, b64, debug_item)

                        if up_url:
                            if not first_img_url:
                                first_img_url = up_url

                            html_parts.append(
                                f'<div style="margin:30px 0; text-align:center;">'
                                f'<img src="{up_url}" style="max-width:100%; height:auto; border-radius:10px;"></div>'
                            )
                    image_debug.append(debug_item)
                else:
                    debug_item["skipped_reason"] = "no_src_or_svg"
                    image_debug.append(debug_item)

                for child in el.find_all():
                    seen.add(child)
                seen.add(el)

        elif "se-text-paragraph" in el.get("class", []):
            raw_html = str(el)
            clean_html = re.sub(r'class="[^"]*"', "", raw_html)
            clean_html = re.sub(r'font-size:[^;"]*;?', "", clean_html)
            html_parts.append(f'<div style="margin-bottom:15px;">{clean_html}</div>')
            seen.add(el)

    html_parts.append("</div>")
    return "\n".join(html_parts), first_img_url, image_debug


# ============================================================================
# 게시글 업로드
# ============================================================================
def upload_article(access_token, board_no, title, content, thumbnail):
    payload = {
        "requests": [
            {
                "shop_no": 1,
                "writer": "관리자",
                "member_id": MALL_ID,
                "title": title,
                "content": content,
                "client_ip": "127.0.0.1",
            }
        ]
    }

    if thumbnail:
        payload["requests"][0]["attach_file_urls"] = [
            {
                "name": "thumbnail.jpg",
                "url": thumbnail,
            }
        ]

    res = requests.post(
        f"https://{MALL_ID}.cafe24api.com/api/v2/admin/boards/{board_no}/articles",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Cafe24-Api-Version": API_VERSION,
        },
        json=payload,
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


# ============================================================================
# HTTP Handler
# ============================================================================
class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send_json(
            200,
            {
                "success": True,
                "message": "debug",
                "env_debug": get_env_debug(),
            },
        )

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            payload = json.loads(raw_body)

            url = str(payload.get("url", "")).strip()
            board_no = int(payload.get("boardNo", 8))

            if not url:
                self._send_json(400, {"success": False, "message": "블로그 주소를 입력해 주세요."})
                return

            if board_no < 1:
                self._send_json(400, {"success": False, "message": "게시판 번호가 올바르지 않습니다."})
                return

            access_token = refresh_access_token()
            real_url = normalize_naver_url(url)
            title = extract_title(real_url)
            final_html, thumb_url, image_debug = build_final_content(access_token, real_url)

            result = upload_article(
                access_token=access_token,
                board_no=board_no,
                title=title,
                content=final_html,
                thumbnail=thumb_url,
            )

            self._send_json(
                200,
                {
                    "success": True,
                    "title": title,
                    "boardNo": board_no,
                    "sourceUrl": real_url,
                    "debug": {
                        "thumbnail": thumb_url,
                        "image_debug": image_debug,
                    },
                    "result": result,
                },
            )

        except ValueError as e:
            message = str(e)
            try:
                parsed = json.loads(message)
                self._send_json(400, {"success": False, **parsed})
            except Exception:
                self._send_json(400, {"success": False, "message": message})

        except requests.HTTPError as e:
            detail = ""
            try:
                detail = str(e)
            except Exception:
                try:
                    detail = e.response.text
                except Exception:
                    detail = "HTTPError"

            self._send_json(
                500,
                {
                    "success": False,
                    "message": "외부 API 호출 중 오류가 발생했습니다.",
                    "detail": detail,
                },
            )

        except Exception as e:
            self._send_json(500, {"success": False, "message": str(e)})
