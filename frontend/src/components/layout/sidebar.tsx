"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Menu,
    Plus,
    MessageSquare,
    Settings,
    User,
    Library,
    Info
} from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

export function Sidebar() {
    const pathname = usePathname();
    const [isCollapsed, setIsCollapsed] = useState(false);

    const toggleSidebar = () => setIsCollapsed(!isCollapsed);

    const navItems = [
        { icon: MessageSquare, label: "Recent Chats", href: "/chat" },
        { icon: Library, label: "Library", href: "/library" },
        { icon: Info, label: "About Us", href: "/about" },
    ];

    const bottomItems = [
        { icon: Settings, label: "Settings", href: "/settings" },
        { icon: User, label: "Profile", href: "/profile" },
    ];

    return (
        <motion.aside
            initial={{ width: 280 }}
            animate={{ width: isCollapsed ? 80 : 280 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="relative flex h-screen flex-col border-r bg-[#f0f4f9] py-4 text-slate-700"
        >
            {/* Header / Toggle */}
            <div className="flex items-center px-4 mb-8">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleSidebar}
                    className="hover:bg-slate-200 rounded-full"
                >
                    <Menu className="h-6 w-6 text-slate-600" />
                </Button>
                <AnimatePresence>
                    {!isCollapsed && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="ml-4"
                        >
                            {/* Logo removed from here as requested */}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* New Chat Button */}
            <div className="px-4 mb-6">
                <Link href="/">
                    <div
                        className={cn(
                            "flex items-center rounded-full bg-[#dde3ea] p-3 text-sm font-medium text-slate-700 transition-colors hover:bg-[#d0d7de] cursor-pointer",
                            isCollapsed ? "justify-center" : "space-x-3 px-4"
                        )}
                    >
                        <Plus className="h-5 w-5 text-slate-600" />
                        {!isCollapsed && <span>New chat</span>}
                    </div>
                </Link>
            </div>

            {/* Main Nav */}
            <nav className="flex-1 space-y-1 px-3">
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            "flex items-center rounded-full p-3 text-sm font-medium transition-colors hover:bg-[#dde3ea]",
                            pathname === item.href ? "bg-[#cce8ff] text-[#001d35]" : "text-slate-600",
                            isCollapsed ? "justify-center" : "space-x-3 px-4"
                        )}
                    >
                        <item.icon className="h-5 w-5" />
                        {!isCollapsed && <span>{item.label}</span>}
                    </Link>
                ))}
            </nav>

            {/* Bottom Nav */}
            <div className="mt-auto px-3 space-y-1">
                {bottomItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            "flex items-center rounded-full p-3 text-sm font-medium transition-colors hover:bg-[#dde3ea] text-slate-600",
                            isCollapsed ? "justify-center" : "space-x-3 px-4"
                        )}
                    >
                        <item.icon className="h-5 w-5" />
                        {!isCollapsed && <span>{item.label}</span>}
                    </Link>
                ))}

                {/* Location / Footer Info */}
                {!isCollapsed && (
                    <div className="mt-4 px-4 text-xs text-slate-400">
                        <p>CRDC Knowledge Hub</p>
                        <p>Brisbane, QLD</p>
                    </div>
                )}
            </div>
        </motion.aside>
    );
}
