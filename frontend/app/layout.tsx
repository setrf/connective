import type { Metadata } from "next";
import { Inter, Space_Mono } from "next/font/google";
import "./globals.css";
import { SessionProvider } from "@/providers/session-provider";
import { AuthProvider } from "@/providers/auth-provider";

const inter = Inter({ subsets: ["latin"] });
const spaceMono = Space_Mono({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-space-mono",
});

export const metadata: Metadata = {
  title: "Connective",
  description: "Discover work overlap across your tools",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="antialiased">
      <body className={`${inter.className} ${spaceMono.variable}`}>
        <SessionProvider>
          <AuthProvider>{children}</AuthProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
