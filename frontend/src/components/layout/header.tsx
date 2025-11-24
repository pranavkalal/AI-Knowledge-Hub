"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export function Header() {
    const pathname = usePathname();
    const isChat = pathname?.startsWith("/chat");

    return (
        <header
            className={cn(
                "sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 transition-all duration-300",
                isChat && "border-transparent bg-transparent hover:bg-background/95 hover:border-b opacity-0 hover:opacity-100 absolute top-0"
            )}
        >
            <div className="container flex h-14 items-center">
                <Link href="/" className="mr-6 flex items-center space-x-3">
                    <img src="/logo.png" alt="CRDC Logo" className="h-10 w-auto object-contain" />
                    <div className="hidden h-8 w-px bg-slate-200 sm:block" />
                    <span className="hidden font-semibold tracking-tight sm:inline-block text-slate-900">
                        Knowledge Hub
                    </span>
                </Link>
                <nav className="flex items-center space-x-6 text-sm font-medium">
                    <Link
                        href="/chat"
                        className="transition-colors hover:text-[#692080] text-foreground/60"
                    >
                        Research Assistant
                    </Link>
                    <Link
                        href="/library"
                        className="transition-colors hover:text-[#692080] text-foreground/60"
                    >
                        Library
                    </Link>
                    <Link
                        href="/about"
                        className="transition-colors hover:text-[#692080] text-foreground/60"
                    >
                        About Us
                    </Link>
                </nav>
                <div className="ml-auto flex items-center space-x-4">
                    {/* Add UserMenu or Auth buttons here later */}
                </div>
            </div>
        </header>
    );
}
