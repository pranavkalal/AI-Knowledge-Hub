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
    Info,
    Trash2,
    X
} from "lucide-react";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useChatStore } from "@/lib/store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";

// Shared navigation content component
function SidebarNav({
    isCollapsed = false,
    onLinkClick
}: {
    isCollapsed?: boolean;
    onLinkClick?: () => void;
}) {
    const pathname = usePathname();
    const { sessions, deleteSession } = useChatStore();
    const recentChats = sessions.slice(0, 5);

    const navItems = [
        { icon: Library, label: "Library", href: "/library" },
        { icon: Info, label: "About Us", href: "/about" },
    ];

    const bottomItems = [
        { icon: Settings, label: "Settings", href: "/settings" },
        { icon: User, label: "Profile", href: "/profile" },
    ];

    return (
        <>
            {/* New Chat Button */}
            <div className="px-4 mb-6">
                <Link href="/" onClick={onLinkClick}>
                    <div
                        className={cn(
                            "flex items-center rounded-full bg-slate-200 dark:bg-slate-800 p-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition-colors hover:bg-slate-300 dark:hover:bg-slate-700 cursor-pointer",
                            isCollapsed ? "justify-center" : "space-x-3 px-4"
                        )}
                    >
                        <Plus className="h-5 w-5 text-slate-600 dark:text-slate-300" />
                        {!isCollapsed && <span>New chat</span>}
                    </div>
                </Link>
            </div>

            {/* Main Nav */}
            <nav className="flex-1 space-y-1 px-3 overflow-hidden">
                {/* Recent Chats Section */}
                {!isCollapsed && recentChats.length > 0 && (
                    <div className="mb-4">
                        <p className="px-4 text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                            Recent Chats
                        </p>
                        <ScrollArea className="h-[180px]">
                            {recentChats.map((chat) => (
                                <div
                                    key={chat.id}
                                    className="group flex items-center justify-between rounded-lg p-2 px-3 text-sm transition-colors hover:bg-slate-200 dark:hover:bg-slate-700"
                                >
                                    <Link
                                        href={`/chat?session=${chat.id}`}
                                        onClick={onLinkClick}
                                        className="flex-1 truncate text-slate-600 dark:text-slate-300"
                                    >
                                        {chat.title}
                                    </Link>
                                    <button
                                        onClick={(e) => {
                                            e.preventDefault();
                                            deleteSession(chat.id);
                                        }}
                                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-all"
                                        aria-label="Delete chat"
                                    >
                                        <Trash2 className="h-3 w-3 text-red-500" />
                                    </button>
                                </div>
                            ))}
                        </ScrollArea>
                    </div>
                )}

                {isCollapsed && (
                    <Link
                        href="/chat"
                        onClick={onLinkClick}
                        className={cn(
                            "flex items-center rounded-full p-3 text-sm font-medium transition-colors hover:bg-slate-200 dark:hover:bg-slate-700 justify-center",
                            pathname.startsWith("/chat") ? "bg-purple-100 dark:bg-purple-900/30 text-purple-900 dark:text-purple-100" : "text-slate-600 dark:text-slate-300"
                        )}
                    >
                        <MessageSquare className="h-5 w-5" />
                    </Link>
                )}

                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        onClick={onLinkClick}
                        className={cn(
                            "flex items-center rounded-full p-3 text-sm font-medium transition-colors hover:bg-slate-200 dark:hover:bg-slate-700",
                            pathname === item.href ? "bg-purple-100 dark:bg-purple-900/30 text-purple-900 dark:text-purple-100" : "text-slate-600 dark:text-slate-300",
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
                {/* Theme Toggle */}
                <ThemeToggle collapsed={isCollapsed} />

                {bottomItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        onClick={onLinkClick}
                        className={cn(
                            "flex items-center rounded-full p-3 text-sm font-medium transition-colors hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300",
                            isCollapsed ? "justify-center" : "space-x-3 px-4"
                        )}
                    >
                        <item.icon className="h-5 w-5" />
                        {!isCollapsed && <span>{item.label}</span>}
                    </Link>
                ))}

                {/* Location / Footer Info */}
                {!isCollapsed && (
                    <div className="mt-4 px-4 text-xs text-slate-400 dark:text-slate-500">
                        <p>CRDC Knowledge Hub</p>
                        <p>Brisbane, QLD</p>
                    </div>
                )}
            </div>
        </>
    );
}

// Mobile Header with Sheet
function MobileSidebar() {
    const [open, setOpen] = useState(false);

    return (
        <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-slate-100 dark:bg-slate-900 border-b dark:border-slate-700 px-4 py-3 flex items-center justify-between">
            <Sheet open={open} onOpenChange={setOpen}>
                <SheetTrigger asChild>
                    <Button variant="ghost" size="icon" className="hover:bg-slate-200 dark:hover:bg-slate-800">
                        <Menu className="h-6 w-6 text-slate-600 dark:text-slate-300" />
                        <span className="sr-only">Open menu</span>
                    </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-72 p-0 bg-slate-100 dark:bg-slate-900">
                    <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
                    <div className="flex flex-col h-full py-4">
                        <SidebarNav onLinkClick={() => setOpen(false)} />
                    </div>
                </SheetContent>
            </Sheet>

            <Link href="/" className="flex items-center gap-2">
                <img src="/logo.png" alt="CRDC" className="h-8 dark:invert" />
            </Link>

            <div className="w-10" /> {/* Spacer for centering */}
        </div>
    );
}

// Desktop Sidebar
function DesktopSidebar() {
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <motion.aside
            initial={{ width: 220 }}
            animate={{ width: isCollapsed ? 60 : 220 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="hidden md:flex sticky top-0 h-screen flex-col border-r bg-slate-100 dark:bg-slate-900 py-4 text-slate-700 dark:text-slate-200 flex-shrink-0"
        >
            {/* Header / Toggle */}
            <div className="flex items-center px-4 mb-8">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full"
                    aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                    <Menu className="h-6 w-6 text-slate-600 dark:text-slate-300" />
                </Button>
                <AnimatePresence>
                    {!isCollapsed && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="ml-4"
                        >
                            <Link href="/" className="flex items-center gap-2">
                                <img src="/logo.png" alt="CRDC" className="h-8 dark:invert" />
                            </Link>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <SidebarNav isCollapsed={isCollapsed} />
        </motion.aside>
    );
}

export function Sidebar() {
    return (
        <>
            <MobileSidebar />
            <DesktopSidebar />
        </>
    );
}
