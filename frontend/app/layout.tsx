import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "カウンセリング対話エージェント",
  description: "対話エージェントとテキストチャットを行うWebアプリケーション",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
