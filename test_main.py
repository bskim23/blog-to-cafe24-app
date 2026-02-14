name: Naver to Cafe24 Auto Post

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  auto-post:
    runs-on: ubuntu-latest
    
    steps:
      - name: 코드 체크아웃
        uses: actions/checkout@v3
      
      - name: Python 3.10 설정
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: 패키지 설치
        run: |
          pip install requests beautifulsoup4 PyGithub
      
      - name: 테스트 실행  # ← 이름 변경
        env:
          CAFE24_CLIENT_ID: ${{ secrets.CAFE24_CLIENT_ID }}
          CAFE24_CLIENT_SECRET: ${{ secrets.CAFE24_CLIENT_SECRET }}
          CAFE24_MALL_ID: ${{ secrets.CAFE24_MALL_ID }}
          CAFE24_REFRESH_TOKEN: ${{ secrets.CAFE24_REFRESH_TOKEN }}
          PA_TOKEN: ${{ secrets.PA_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
        run: python -u test_main.py  # ← 파일명 변경
