import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "블로그 → 카페24 업로드",
  description: "네이버 블로그 글 주소를 입력해 카페24 게시판에 업로드하는 앱",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
