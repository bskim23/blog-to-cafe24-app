name: Blog to Cafe24 Auto Post

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  update-token-and-post:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install requests

      - name: Run script
        env:
          CAFE24_MALL_ID: ${{ secrets.CAFE24_MALL_ID }}
          CAFE24_CLIENT_ID: ${{ secrets.CAFE24_CLIENT_ID }}
          CAFE24_CLIENT_SECRET: ${{ secrets.CAFE24_CLIENT_SECRET }}
          CAFE24_REFRESH_TOKEN: ${{ secrets.CAFE24_REFRESH_TOKEN }}
        run: python main.py

      # [중요] 글쓰기가 실패해도 토큰은 무조건 갱신하여 저장합니다.
      - name: Update Refresh Token Secret
        if: always()
        env:
          GH_TOKEN: ${{ secrets.PA_TOKEN }}
        run: |
          if [ -n "$NEW_REFRESH_TOKEN" ]; then
            echo "🔄 새 토큰을 깃허브 금고(Secrets)에 저장합니다..."
            gh secret set CAFE24_REFRESH_TOKEN --body "$NEW_REFRESH_TOKEN"
            echo "✅ 토큰 갱신 완료!"
          else
            echo "⚠️ 저장할 새 토큰이 없습니다."
          fi
