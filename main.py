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
        original_size = len(att['file_data']) * 3 / 4
        print(f"      추정 원본 크기: {original_size:,.0f} bytes ({original_size/1024/1024:.2f} MB)")
    
    # 본문 구성 (원문 링크 추가)
    final_content = f"{content}\n\n<br><br><a href='{original_link}' target='_blank'>📝 원문 보러가기</a>"
    
    print(f"\n🔍 [DEBUG] 최종 본문 길이: {len(final_content):,}자")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔧 시도 1: shop_no를 request 밖으로 (구조 변경)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    payload_v1 = {
        "shop_no": 1,
        "request": {
            "board_no": BOARD_NO,
            "title": title,
            "content": final_content,
            "writer": WRITER_NAME,
            "password": PASSWORD,
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments
        }
    }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔧 시도 2: shop_no 제거 (일부 API는 불필요)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    payload_v2 = {
        "request": {
            "board_no": BOARD_NO,
            "title": title,
            "content": final_content,
            "writer": WRITER_NAME,
            "password": PASSWORD,
            "is_notice": "F",
            "is_secret": "F",
            "attachments": attachments
        }
    }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔧 시도 3: request 래핑 제거 (flat 구조)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    payload_v3 = {
        "shop_no": 1,
        "board_no": BOARD_NO,
        "title": title,
        "content": final_content,
        "writer": WRITER_NAME,
        "password": PASSWORD,
        "is_notice": "F",
        "is_secret": "F",
        "attachments": attachments
    }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 기본 payload 선택 (v1)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    payload = payload_v1
    
    print(f"\n🔍 [DEBUG] Payload 구성 완료:")
    print(f"   shop_no: 1")
    print(f"   board_no: {BOARD_NO}")
    print(f"   title: {title}")
    print(f"   content 길이: {len(final_content)} chars")
    print(f"   writer: {WRITER_NAME}")
    print(f"   password: {PASSWORD}")
    print(f"   is_notice: F")
    print(f"   is_secret: F")
    print(f"   attachments: {len(attachments)}개")
    
    # Payload 샘플 출력
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
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔧 API 버전 헤더 추가!
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": "2025-12-01"  # ← 추가!
    }
    
    print(f"\n🔍 [DEBUG] API URL: {url}")
    print(f"🔍 [DEBUG] Headers:")
    print(f"   Authorization: Bearer {access_token[:20]}...")
    print(f"   Content-Type: application/json")
    print(f"   X-Cafe24-Api-Version: 2025-12-01")  # ← 추가!
    print(f"\n🔍 [DEBUG] POST 요청 전송 중 (Payload v1)...")
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\n🔍 [DEBUG] 응답 상태 코드: {res.status_code}")
        
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
            return
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # v1 실패 시 v2 시도
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if res.status_code == 422:
            print(f"\n⚠️  Payload v1 실패 (422), v2 시도 중...")
            print(f"🔍 [DEBUG] v1 응답: {res.text}")
            
            print(f"\n🔍 [DEBUG] Payload v2 시도 (shop_no 제거)...")
            res = requests.post(url, headers=headers, json=payload_v2, timeout=30)
            print(f"🔍 [DEBUG] v2 응답 상태: {res.status_code}")
            
            if res.status_code == 201:
                print("\n🎉 v2로 성공!")
                print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/")
                return
            
            print(f"🔍 [DEBUG] v2 응답: {res.text}")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # v2도 실패 시 v3 시도
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            print(f"\n⚠️  Payload v2도 실패, v3 시도 중...")
            print(f"🔍 [DEBUG] Payload v3 시도 (flat 구조)...")
            res = requests.post(url, headers=headers, json=payload_v3, timeout=30)
            print(f"🔍 [DEBUG] v3 응답 상태: {res.status_code}")
            
            if res.status_code == 201:
                print("\n🎉 v3로 성공!")
                print(f"   🔗 확인: https://{MALL_ID}.cafe24.com/board/gallery/{BOARD_NO}/")
                return
            
            print(f"🔍 [DEBUG] v3 응답: {res.text}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 모든 시도 실패
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print(f"\n❌ [ERROR] 모든 Payload 버전 실패 (HTTP {res.status_code})")
        print(f"\n🔍 [DEBUG] 최종 응답 헤더:")
        for key, value in res.headers.items():
            print(f"   {key}: {value}")
        
        print(f"\n🔍 [DEBUG] 최종 응답 내용:")
        try:
            error_json = res.json()
            print(json.dumps(error_json, indent=2, ensure_ascii=False))
        except:
            print(res.text)
        
        print(f"\n⚠️  [추가 확인 사항]")
        print(f"   1. 카페24 관리자 → 게시판 8 → 설정 확인")
        print(f"   2. 게시글 작성 권한 (회원만 가능? 비회원 가능?)")
        print(f"   3. 게시판 유형이 정말 갤러리인지 확인")
        print(f"   4. API 접근 권한 확인")
        
        sys.exit(1)
            
    except Exception as e:
        print(f"❌ [ERROR] 업로드 요청 실패: {e}")
        print(f"🔍 [DEBUG] Exception Type: {type(e).__name__}")
        import traceback
        print(f"🔍 [DEBUG] Traceback:\n{traceback.format_exc()}")
        sys.exit(1)
