import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "CRDC Knowledge Hub",
  description: "AI-Powered Research Assistant for Australian Cotton",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          inter.variable
        )}
      >
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container flex h-14 items-center">
            <Link href="/" className="mr-6 flex items-center space-x-2">
              {/* CRDC Logo Placeholder */}
              <div className="h-8 w-8 rounded-full bg-[#009B77] flex items-center justify-center text-white font-bold text-xs">
                CRDC
              </div>
              <span className="hidden font-bold sm:inline-block text-slate-900">
                Knowledge Hub
              </span>
            </Link>
            <nav className="flex items-center space-x-6 text-sm font-medium">
              <Link
                href="/chat"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                Research Assistant
              </Link>
              <Link
                href="/library"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                Library
              </Link>
            </nav>
            <div className="ml-auto flex items-center space-x-4">
              {/* Add UserMenu or Auth buttons here later */}
            </div>
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
