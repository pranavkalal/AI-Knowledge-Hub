import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { cn } from "@/lib/utils";

import { Sidebar } from "@/components/layout/sidebar";

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
          "flex min-h-screen bg-white font-sans antialiased",
          inter.variable
        )}
      >
        <Sidebar />
        <main className="flex-1 overflow-auto bg-white">{children}</main>
      </body>
    </html>
  );
}
