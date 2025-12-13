"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, AlertCircle, Sparkles, Users, Copy, Check, ThumbsUp, ThumbsDown, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useState, useEffect, useRef, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PersonaType, Citation } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useChat } from "ai/react";

// Persona-specific configurations
const personaConfig: Record<PersonaType, { placeholder: string }> = {
    grower: {
        placeholder: "Ask about managing pests, irrigation, or soil health...",
    },
    researcher: {
        placeholder: "Ask about research findings, methodologies, or data...",
    },
    extension_officer: {
        placeholder: "Ask about recommendations to share with growers...",
    },
};

interface ChatInterfaceProps {
    initialQuery: string;
    initialPersona?: PersonaType;
    onCitationClick: (docId: string, page?: number, bbox?: number[]) => void;
    sessionId?: string;
    existingMessages?: any[];
}

// Copy button component
function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        toast.success("Copied to clipboard");
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            onClick={handleCopy}
            className="p-1.5 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 transition-colors"
            aria-label="Copy to clipboard"
        >
            {copied ? (
                <Check className="h-4 w-4 text-green-500" />
            ) : (
                <Copy className="h-4 w-4" />
            )}
        </button>
    );
}

// Extract citations from message content
function extractCitations(content: string): { cleanContent: string; citations: Citation[] } {
    const citationMatch = content.match(/<!--CITATIONS:(.*)-->$/);
    if (citationMatch) {
        try {
            const citations = JSON.parse(citationMatch[1]);
            const cleanContent = content.replace(/<!--CITATIONS:.*-->$/, '').trim();
            return { cleanContent, citations };
        } catch (e) {
            console.error('Failed to parse citations:', e);
        }
    }
    return { cleanContent: content, citations: [] };
}

export function ChatInterface({ initialQuery, initialPersona = "grower", onCitationClick, sessionId }: ChatInterfaceProps) {
    const [persona, setPersona] = useState<PersonaType>(initialPersona);
    const [messageFeedback, setMessageFeedback] = useState<Record<string, "up" | "down" | null>>({});
    const scrollRef = useRef<HTMLDivElement>(null);
    const hasInitialized = useRef(false);

    const currentConfig = useMemo(() => personaConfig[persona], [persona]);

    // Use AI SDK's useChat hook
    const { messages, input, handleInputChange, handleSubmit, isLoading, reload, setMessages } = useChat({
        api: '/api/chat',
        id: sessionId,
        body: {
            persona,
            sessionId
        },
        onFinish: (message) => {
            // Citations are already in the message content
            console.log('Message finished:', message);
        },
        onError: (error) => {
            toast.error("Failed to get response from Knowledge Hub");
            console.error("Chat error:", error);
        }
    });

    // Handle initial query
    useEffect(() => {
        if (initialQuery && messages.length === 0 && !hasInitialized.current) {
            hasInitialized.current = true;
            // Trigger submit with initial query
            const event = new Event('submit', { bubbles: true, cancelable: true });
            Object.defineProperty(event, 'target', {
                value: { elements: { message: { value: initialQuery } } },
                writable: false
            });
            handleSubmit(event as any, { data: { persona } });
        }
    }, [initialQuery, messages.length, handleSubmit, persona]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages.length, isLoading]);

    // Handle feedback submission
    const handleFeedback = async (messageId: string, score: number, currentFeedback: "up" | "down" | null) => {
        const newFeedback = currentFeedback === (score > 0 ? "up" : "down") ? null : (score > 0 ? "up" : "down");
        setMessageFeedback(prev => ({ ...prev, [messageId]: newFeedback }));

        if (newFeedback) {
            const message = messages.find(m => m.id === messageId);
            try {
                await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message_id: messageId,
                        session_id: sessionId,
                        score,
                        question: messages[messages.findIndex(m => m.id === messageId) - 1]?.content,
                        answer: message?.content
                    })
                });
                toast.success(score > 0 ? "Thanks for your feedback!" : "We'll use this to improve");
            } catch (error) {
                console.error('Failed to submit feedback:', error);
            }
        }
    };

    return (
        <div className="flex h-full flex-col bg-background relative">
            <ScrollArea className="flex-1 px-4 sm:px-0">
                <div className="flex flex-col space-y-8 pb-32 pt-8 max-w-3xl mx-auto">
                    {/* Logo Area */}
                    <div className="flex justify-start mb-4">
                        <Link href="/" className="block transition-opacity hover:opacity-80">
                            <img src="/logo.png" alt="CRDC Logo" className="h-8 w-auto object-contain" />
                        </Link>
                    </div>

                    <AnimatePresence initial={false}>
                        {messages.map((msg, idx) => {
                            const { cleanContent, citations } = msg.role === 'assistant'
                                ? extractCitations(msg.content)
                                : { cleanContent: msg.content, citations: [] };

                            return (
                                <motion.div
                                    key={msg.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={`flex gap-4 group ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                                >
                                    {msg.role === "assistant" && (
                                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
                                            <Sparkles className="h-6 w-6 text-[#4285f4] animate-pulse" />
                                        </div>
                                    )}

                                    <div className={`flex max-w-[80%] flex-col gap-2 ${msg.role === "user"
                                        ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white rounded-[20px] px-5 py-3"
                                        : "bg-transparent text-slate-900 dark:text-slate-100 px-0 py-0"
                                        }`}>
                                        <div className="prose prose-slate max-w-none leading-7 text-[16px]">
                                            {cleanContent ? (
                                                <ReactMarkdown>{cleanContent}</ReactMarkdown>
                                            ) : (
                                                isLoading && msg.role === "assistant" && (
                                                    <div className="flex items-center gap-1 h-6">
                                                        <span className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.3s]"></span>
                                                        <span className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.15s]"></span>
                                                        <span className="h-2 w-2 animate-bounce rounded-full bg-blue-400"></span>
                                                    </div>
                                                )
                                            )}
                                        </div>

                                        {citations && citations.length > 0 && (() => {
                                            // Group citations by doc_id, take first citation per doc, limit to 3 sources
                                            const uniqueDocs = new Map<string, typeof citations[0]>();
                                            for (const cite of citations) {
                                                const docId = cite.doc_id || 'unknown';
                                                if (!uniqueDocs.has(docId) && uniqueDocs.size < 3) {
                                                    uniqueDocs.set(docId, cite);
                                                }
                                            }

                                            return (
                                                <div className="mt-4 flex flex-wrap gap-2">
                                                    {Array.from(uniqueDocs.entries()).map(([docId, cite]) => {
                                                        // Clean up doc title
                                                        const title = docId.replace(/_/g, ' ').replace(/\d+$/, '').trim();
                                                        const shortTitle = title.length > 45 ? title.slice(0, 42) + '...' : title;

                                                        return (
                                                            <motion.button
                                                                key={docId}
                                                                whileHover={{ scale: 1.02 }}
                                                                whileTap={{ scale: 0.98 }}
                                                                onClick={() => onCitationClick(cite.doc_id, cite.page, cite.bbox)}
                                                                className="rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 transition-colors hover:bg-purple-50 dark:hover:bg-purple-900/30 hover:border-purple-300 dark:hover:border-purple-600 hover:text-purple-700 dark:hover:text-purple-300"
                                                            >
                                                                {shortTitle}
                                                            </motion.button>
                                                        );
                                                    })}
                                                </div>
                                            );
                                        })()}

                                        {/* Action buttons for assistant messages */}
                                        {msg.role === "assistant" && cleanContent && !isLoading && (
                                            <div className="mt-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <CopyButton text={cleanContent} />

                                                <button
                                                    onClick={() => handleFeedback(msg.id, 1, messageFeedback[msg.id] || null)}
                                                    className={cn(
                                                        "p-1.5 rounded-md transition-colors",
                                                        messageFeedback[msg.id] === "up"
                                                            ? "bg-green-100 dark:bg-green-900/30 text-green-600"
                                                            : "hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
                                                    )}
                                                    aria-label="Good response"
                                                >
                                                    <ThumbsUp className="h-4 w-4" />
                                                </button>

                                                <button
                                                    onClick={() => handleFeedback(msg.id, -1, messageFeedback[msg.id] || null)}
                                                    className={cn(
                                                        "p-1.5 rounded-md transition-colors",
                                                        messageFeedback[msg.id] === "down"
                                                            ? "bg-red-100 dark:bg-red-900/30 text-red-600"
                                                            : "hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
                                                    )}
                                                    aria-label="Poor response"
                                                >
                                                    <ThumbsDown className="h-4 w-4" />
                                                </button>

                                                {/* Regenerate button */}
                                                {idx > 0 && messages[idx - 1]?.role === "user" && (
                                                    <button
                                                        onClick={() => reload()}
                                                        className="p-1.5 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 transition-colors"
                                                        aria-label="Regenerate response"
                                                    >
                                                        <RefreshCw className="h-4 w-4" />
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>

                    <div ref={scrollRef} />
                </div>
            </ScrollArea>

            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background to-transparent pb-6 pt-10 px-4">
                <div className="max-w-3xl mx-auto">
                    <form onSubmit={handleSubmit} className="relative group">
                        <div className="relative flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-4 py-3 transition-all focus-within:bg-slate-200 dark:focus-within:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700">
                            <Input
                                value={input}
                                onChange={handleInputChange}
                                placeholder={currentConfig.placeholder}
                                name="message"
                                className="flex-1 border-none bg-transparent text-lg placeholder:text-slate-500 dark:placeholder:text-slate-400 focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none h-auto py-1 dark:text-white"
                            />
                            <div className="flex items-center space-x-2">
                                <div className="relative">
                                    <select
                                        value={persona}
                                        onChange={(e) => setPersona(e.target.value as PersonaType)}
                                        className="appearance-none bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 pr-8 text-sm text-slate-600 dark:text-slate-200 cursor-pointer hover:border-slate-300 dark:hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
                                    >
                                        <option value="grower">🌱 Grower</option>
                                        <option value="researcher">🔬 Researcher</option>
                                        <option value="extension_officer">📋 Extension</option>
                                    </select>
                                    <Users className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                                </div>
                                <Button
                                    type="submit"
                                    size="icon"
                                    variant="ghost"
                                    disabled={isLoading || !input.trim()}
                                    className={cn(
                                        "h-10 w-10 rounded-full transition-all",
                                        input.trim() ? "bg-[#692080] text-white hover:bg-[#501860]" : "text-slate-400 hover:bg-slate-200"
                                    )}
                                >
                                    <Send className="h-5 w-5" />
                                </Button>
                            </div>
                        </div>
                    </form>
                    <div className="text-center mt-3">
                        <span className="text-[11px] text-slate-400">
                            AI Knowledge Hub can make mistakes. Please verify important information.
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
