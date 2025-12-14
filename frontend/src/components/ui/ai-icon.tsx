"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface AIIconProps {
    isStreaming?: boolean;
    size?: "sm" | "md" | "lg";
    className?: string;
}

/**
 * Gemini-inspired AI icon with streaming animation.
 * Shows animated flowing bars during streaming, static gradient otherwise.
 */
export function AIIcon({ isStreaming = false, size = "md", className }: AIIconProps) {
    const sizeClasses = {
        sm: "h-5 w-5",
        md: "h-6 w-6",
        lg: "h-8 w-8",
    };

    const barSizes = {
        sm: { height: [8, 12, 10, 14], width: 2, gap: 1 },
        md: { height: [10, 16, 12, 18], width: 2.5, gap: 1.5 },
        lg: { height: [12, 20, 16, 22], width: 3, gap: 2 },
    };

    const config = barSizes[size];

    if (isStreaming) {
        return (
            <div className={cn("flex items-center justify-center", sizeClasses[size], className)}>
                <div className="flex items-end justify-center gap-[2px]" style={{ gap: config.gap }}>
                    {[0, 1, 2, 3].map((i) => (
                        <motion.div
                            key={i}
                            className="rounded-full bg-gradient-to-t from-violet-600 via-fuchsia-500 to-amber-400"
                            style={{ width: config.width }}
                            animate={{
                                height: [
                                    config.height[i],
                                    config.height[(i + 2) % 4],
                                    config.height[(i + 1) % 4],
                                    config.height[i],
                                ],
                                opacity: [0.7, 1, 0.8, 0.7],
                            }}
                            transition={{
                                duration: 0.8,
                                repeat: Infinity,
                                ease: "easeInOut",
                                delay: i * 0.1,
                            }}
                        />
                    ))}
                </div>
            </div>
        );
    }

    // Static state: Gemini-style starburst icon
    return (
        <div className={cn("relative flex items-center justify-center", sizeClasses[size], className)}>
            <svg
                viewBox="0 0 24 24"
                fill="none"
                className="w-full h-full"
            >
                <defs>
                    <linearGradient id="ai-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#8B5CF6" />
                        <stop offset="50%" stopColor="#D946EF" />
                        <stop offset="100%" stopColor="#F59E0B" />
                    </linearGradient>
                </defs>
                {/* Four-point star / sparkle shape */}
                <path
                    d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z"
                    fill="url(#ai-gradient)"
                />
                <path
                    d="M19 15L19.75 17.25L22 18L19.75 18.75L19 21L18.25 18.75L16 18L18.25 17.25L19 15Z"
                    fill="url(#ai-gradient)"
                    opacity="0.7"
                />
                <path
                    d="M6 16L6.5 17.5L8 18L6.5 18.5L6 20L5.5 18.5L4 18L5.5 17.5L6 16Z"
                    fill="url(#ai-gradient)"
                    opacity="0.5"
                />
            </svg>
        </div>
    );
}

/**
 * Alternative: Orb-style AI icon with glow effect
 */
export function AIOrb({ isStreaming = false, size = "md", className }: AIIconProps) {
    const sizeClasses = {
        sm: "h-5 w-5",
        md: "h-6 w-6",
        lg: "h-8 w-8",
    };

    return (
        <div className={cn("relative", sizeClasses[size], className)}>
            {/* Glow effect */}
            <motion.div
                className="absolute inset-0 rounded-full bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-400 blur-sm"
                animate={isStreaming ? {
                    scale: [1, 1.3, 1],
                    opacity: [0.5, 0.8, 0.5],
                } : {}}
                transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            {/* Core orb */}
            <motion.div
                className="absolute inset-0 rounded-full bg-gradient-to-br from-violet-600 via-fuchsia-500 to-amber-500"
                animate={isStreaming ? {
                    rotate: 360,
                } : {}}
                transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "linear",
                }}
            />
            {/* Inner highlight */}
            <div className="absolute inset-[2px] rounded-full bg-gradient-to-br from-white/30 to-transparent" />
        </div>
    );
}

/**
 * Google Gemini-style flowing wave icon
 */
export function GeminiIcon({ isStreaming = false, size = "md", className }: AIIconProps) {
    const sizeClasses = {
        sm: "h-5 w-5",
        md: "h-6 w-6",
        lg: "h-8 w-8",
    };

    const colors = [
        "from-blue-500 to-blue-600",
        "from-violet-500 to-purple-600",
        "from-fuchsia-500 to-pink-600",
        "from-orange-400 to-amber-500",
    ];

    return (
        <div className={cn("relative flex items-center justify-center", sizeClasses[size], className)}>
            <svg viewBox="0 0 24 24" className="w-full h-full overflow-visible">
                <defs>
                    <linearGradient id="gemini-blue" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#4285F4" />
                        <stop offset="100%" stopColor="#669DF6" />
                    </linearGradient>
                    <linearGradient id="gemini-purple" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#9B72CB" />
                        <stop offset="100%" stopColor="#A855F7" />
                    </linearGradient>
                    <linearGradient id="gemini-pink" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#D96570" />
                        <stop offset="100%" stopColor="#EC4899" />
                    </linearGradient>
                    <linearGradient id="gemini-orange" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#F59E0B" />
                        <stop offset="100%" stopColor="#FBBF24" />
                    </linearGradient>
                </defs>
                
                {/* Animated flowing paths */}
                {isStreaming ? (
                    <>
                        <motion.path
                            d="M4 12 Q8 6 12 12 Q16 18 20 12"
                            stroke="url(#gemini-blue)"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            fill="none"
                            animate={{
                                d: [
                                    "M4 12 Q8 6 12 12 Q16 18 20 12",
                                    "M4 12 Q8 18 12 12 Q16 6 20 12",
                                    "M4 12 Q8 6 12 12 Q16 18 20 12",
                                ],
                            }}
                            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                        />
                        <motion.path
                            d="M4 12 Q8 8 12 12 Q16 16 20 12"
                            stroke="url(#gemini-purple)"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            fill="none"
                            animate={{
                                d: [
                                    "M4 12 Q8 8 12 12 Q16 16 20 12",
                                    "M4 12 Q8 16 12 12 Q16 8 20 12",
                                    "M4 12 Q8 8 12 12 Q16 16 20 12",
                                ],
                            }}
                            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut", delay: 0.15 }}
                        />
                        <motion.path
                            d="M4 12 Q8 10 12 12 Q16 14 20 12"
                            stroke="url(#gemini-pink)"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            fill="none"
                            animate={{
                                d: [
                                    "M4 12 Q8 10 12 12 Q16 14 20 12",
                                    "M4 12 Q8 14 12 12 Q16 10 20 12",
                                    "M4 12 Q8 10 12 12 Q16 14 20 12",
                                ],
                            }}
                            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
                        />
                    </>
                ) : (
                    /* Static sparkle */
                    <>
                        <path
                            d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z"
                            fill="url(#gemini-purple)"
                        />
                        <path
                            d="M18 14L18.75 16.25L21 17L18.75 17.75L18 20L17.25 17.75L15 17L17.25 16.25L18 14Z"
                            fill="url(#gemini-blue)"
                            opacity="0.8"
                        />
                    </>
                )}
            </svg>
        </div>
    );
}

