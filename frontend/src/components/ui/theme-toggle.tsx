"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
    collapsed?: boolean;
}

export function ThemeToggle({ collapsed = false }: ThemeToggleProps) {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = React.useState(false);

    React.useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return (
            <div
                className={cn(
                    "flex items-center rounded-full p-3 text-sm font-medium text-slate-600",
                    collapsed ? "justify-center" : "space-x-3 px-4"
                )}
            >
                <div className="h-5 w-5 animate-pulse bg-slate-200 rounded" />
                {!collapsed && <span className="text-slate-400">Loading...</span>}
            </div>
        );
    }

    const isDark = theme === "dark";

    return (
        <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className={cn(
                "flex items-center rounded-full p-3 text-sm font-medium transition-colors hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 w-full",
                collapsed ? "justify-center" : "space-x-3 px-4"
            )}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
            {isDark ? (
                <Sun className="h-5 w-5" />
            ) : (
                <Moon className="h-5 w-5" />
            )}
            {!collapsed && <span>{isDark ? "Light Mode" : "Dark Mode"}</span>}
        </button>
    );
}



