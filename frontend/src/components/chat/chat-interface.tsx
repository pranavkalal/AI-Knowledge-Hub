"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, AlertCircle, Users, Copy, Check, ThumbsUp, ThumbsDown, RefreshCw } from "lucide-react";
import { GeminiIcon } from "@/components/ui/ai-icon";
import Link from "next/link";
import { useState, useEffect, useRef, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_BASE, Citation, PersonaType } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { useChatStore, ChatMessage } from "@/lib/store";
import { toast } from "sonner";

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
    existingMessages?: ChatMessage[];
}

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    error?: boolean;
    isStreaming?: boolean;
    feedback?: "up" | "down" | null;
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

export function ChatInterface({ initialQuery, initialPersona = "grower", onCitationClick, sessionId, existingMessages }: ChatInterfaceProps) {
    const [query, setQuery] = useState(initialQuery);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [persona, setPersona] = useState<PersonaType>(initialPersona);
    const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(sessionId);
    const scrollRef = useRef<HTMLDivElement>(null);
    const hasInitialized = useRef(false);
    const abortController = useRef<AbortController | null>(null);

    const { createSession, addMessage, updateMessage } = useChatStore();
    const currentConfig = useMemo(() => personaConfig[persona], [persona]);

    // Load existing messages if resuming a session
    useEffect(() => {
        if (existingMessages && existingMessages.length > 0) {
            setMessages(existingMessages.map(m => ({
                id: m.id,
                role: m.role,
                content: m.content,
                citations: m.citations,
                error: m.error,
            })));
            hasInitialized.current = true;
        }
    }, [existingMessages]);

    useEffect(() => {
        if (initialQuery && messages.length === 0 && !hasInitialized.current) {
            hasInitialized.current = true;
            handleSend(initialQuery);
        }
    }, [initialQuery]);

    // Auto-scroll to bottom only when a new message starts or loading state changes
    useEffect(() => {
        if (scrollRef.current) {
            // Only scroll smoothly when loading starts/stops or a new message is added (length changes)
            // We avoid scrolling on every token update to prevent "forced" scrolling
            scrollRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages.length, isLoading]);

    const handleSend = async (text: string) => {
        if (!text.trim()) return;

        // Abort previous request if any
        if (abortController.current) {
            abortController.current.abort();
        }
        abortController.current = new AbortController();

        // Create session if needed
        let activeSessionId = currentSessionId;
        if (!activeSessionId) {
            activeSessionId = createSession(persona, text);
            setCurrentSessionId(activeSessionId);
        }

        const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
        setMessages((prev) => [...prev, userMsg]);
        setQuery("");
        setIsLoading(true);

        // Persist user message to store
        addMessage(activeSessionId, { id: userMsg.id, role: "user", content: text });

        // Create placeholder for AI response
        const aiMsgId = (Date.now() + 1).toString();
        const aiMsg: Message = {
            id: aiMsgId,
            role: "assistant",
            content: "",
            citations: [],
            isStreaming: true
        };
        setMessages((prev) => [...prev, aiMsg]);

        try {
            const response = await fetch(`${API_BASE}/ask?stream=true`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: text,
                    k: 5,
                    mode: "dense",
                    rerank: true,
                    persona: persona
                }),
                signal: abortController.current.signal
            });

            if (!response.ok) throw new Error(response.statusText);
            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let currentContent = "";
            let currentCitations: Citation[] = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Split by newline to handle data: ... lines
                // This is more robust than splitting by \n\n which might fail if chunks are split weirdly
                const lines = buffer.split("\n");

                // Keep the last line in the buffer as it might be incomplete
                buffer = lines.pop() || "";

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (!trimmedLine || !trimmedLine.startsWith("data: ")) continue;

                    const dataStr = trimmedLine.slice(6);
                    if (dataStr === "[DONE]") continue;

                    try {
                        const data = JSON.parse(dataStr);

                        if (data.type === "token") {
                            currentContent += data.token;
                            setMessages((prev) => prev.map(msg =>
                                msg.id === aiMsgId
                                    ? { ...msg, content: currentContent }
                                    : msg
                            ));
                        } else if (data.type === "sources") {
                            currentCitations = data.data;
                            setMessages((prev) => prev.map(msg =>
                                msg.id === aiMsgId
                                    ? { ...msg, citations: currentCitations }
                                    : msg
                            ));
                        } else if (data.type === "error") {
                            throw new Error(data.message);
                        }
                    } catch (e) {
                        console.warn("Failed to parse SSE message:", e);
                    }
                }
            }
        } catch (error: any) {
            if (error.name === 'AbortError') return;
            console.error("Chat Error:", error);
            const errorContent = "Sorry, I encountered an error connecting to the Knowledge Hub. Please try again.";
            setMessages((prev) => prev.map(msg =>
                msg.id === aiMsgId
                    ? { ...msg, content: errorContent, error: true }
                    : msg
            ));
            // Persist error message to store
            if (activeSessionId) {
                addMessage(activeSessionId, { id: aiMsgId, role: "assistant", content: errorContent, error: true });
            }
            toast.error("Failed to get response from Knowledge Hub");
        } finally {
            setIsLoading(false);
            // Get final message content and persist to store
            let finalMessageContent: string | null = null;
            let finalCitations: Citation[] | undefined = undefined;

            setMessages((prev) => {
                const finalMsg = prev.find(m => m.id === aiMsgId);
                if (finalMsg && !finalMsg.error) {
                    finalMessageContent = finalMsg.content;
                    finalCitations = finalMsg.citations;
                }
                return prev.map(msg =>
                    msg.id === aiMsgId ? { ...msg, isStreaming: false } : msg
                );
            });

            // Persist to store after state update completes
            if (finalMessageContent && activeSessionId) {
                addMessage(activeSessionId, {
                    id: aiMsgId,
                    role: "assistant",
                    content: finalMessageContent,
                    citations: finalCitations
                });
            }

            abortController.current = null;
        }
    };

    return (
        <div className="flex h-full flex-col bg-background relative">
            <ScrollArea className="flex-1 px-4 sm:px-0">
                <div className="flex flex-col space-y-8 pb-32 pt-8 max-w-3xl mx-auto">
                    <AnimatePresence initial={false}>
                        {messages.map((msg) => (
                            <motion.div
                                key={msg.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex gap-4 group ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                {msg.role === "assistant" && (
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
                                        {msg.error ? (
                                            <AlertCircle className="h-6 w-6 text-red-500" />
                                        ) : (
                                            <GeminiIcon
                                                isStreaming={msg.isStreaming || (isLoading && !msg.content)}
                                                size="md"
                                            />
                                        )}
                                    </div>
                                )}

                                <div className={`flex max-w-[80%] flex-col gap-2 ${msg.role === "user"
                                    ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white rounded-[20px] px-5 py-3"
                                    : "bg-transparent text-slate-900 dark:text-slate-100 px-0 py-0"
                                    }`}>
                                    <div className="prose prose-slate max-w-none leading-7 text-[16px]">
                                        {msg.content ? (
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        ) : (
                                            isLoading && msg.role === "assistant" && !msg.error && (
                                                <div className="space-y-3 py-1 min-w-[200px]">
                                                    <div className="h-4 w-3/4 rounded-md bg-gradient-to-r from-slate-200 via-slate-300 to-slate-200 dark:from-slate-700 dark:via-slate-600 dark:to-slate-700 animate-shimmer bg-[length:200%_100%]"></div>
                                                    <div className="h-4 w-full rounded-md bg-gradient-to-r from-slate-200 via-slate-300 to-slate-200 dark:from-slate-700 dark:via-slate-600 dark:to-slate-700 animate-shimmer bg-[length:200%_100%] [animation-delay:0.1s]"></div>
                                                    <div className="h-4 w-2/3 rounded-md bg-gradient-to-r from-slate-200 via-slate-300 to-slate-200 dark:from-slate-700 dark:via-slate-600 dark:to-slate-700 animate-shimmer bg-[length:200%_100%] [animation-delay:0.2s]"></div>
                                                </div>
                                            )
                                        )}
                                    </div>

                                    {msg.citations && msg.citations.length > 0 && (() => {
                                        // Group citations by doc_id, take first citation per doc, limit to 3 sources
                                        const uniqueDocs = new Map<string, typeof msg.citations[0]>();
                                        for (const cite of msg.citations) {
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
                                    {msg.role === "assistant" && msg.content && !msg.isStreaming && (
                                        <div className="mt-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <CopyButton text={msg.content} />

                                            <button
                                                onClick={() => {
                                                    setMessages(prev => prev.map(m =>
                                                        m.id === msg.id ? { ...m, feedback: m.feedback === "up" ? null : "up" } : m
                                                    ));
                                                    if (msg.feedback !== "up") toast.success("Thanks for your feedback!");
                                                }}
                                                className={cn(
                                                    "p-1.5 rounded-md transition-colors",
                                                    msg.feedback === "up"
                                                        ? "bg-green-100 dark:bg-green-900/30 text-green-600"
                                                        : "hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
                                                )}
                                                aria-label="Good response"
                                            >
                                                <ThumbsUp className="h-4 w-4" />
                                            </button>

                                            <button
                                                onClick={() => {
                                                    setMessages(prev => prev.map(m =>
                                                        m.id === msg.id ? { ...m, feedback: m.feedback === "down" ? null : "down" } : m
                                                    ));
                                                    if (msg.feedback !== "down") toast.info("We'll use this to improve");
                                                }}
                                                className={cn(
                                                    "p-1.5 rounded-md transition-colors",
                                                    msg.feedback === "down"
                                                        ? "bg-red-100 dark:bg-red-900/30 text-red-600"
                                                        : "hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
                                                )}
                                                aria-label="Poor response"
                                            >
                                                <ThumbsDown className="h-4 w-4" />
                                            </button>

                                            {/* Regenerate button - find the previous user message */}
                                            {(() => {
                                                const msgIndex = messages.findIndex(m => m.id === msg.id);
                                                const prevUserMsg = msgIndex > 0 ? messages[msgIndex - 1] : null;
                                                if (prevUserMsg?.role === "user") {
                                                    return (
                                                        <button
                                                            onClick={() => {
                                                                // Remove this message and regenerate
                                                                setMessages(prev => prev.filter(m => m.id !== msg.id));
                                                                handleSend(prevUserMsg.content);
                                                            }}
                                                            className="p-1.5 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 transition-colors"
                                                            aria-label="Regenerate response"
                                                        >
                                                            <RefreshCw className="h-4 w-4" />
                                                        </button>
                                                    );
                                                }
                                                return null;
                                            })()}
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>



                    <div ref={scrollRef} />
                </div>
            </ScrollArea>

            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background to-transparent pb-6 pt-10 px-4">
                <div className="max-w-3xl mx-auto">
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            handleSend(query);
                        }}
                        className="relative group"
                    >
                        <div className="relative flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-4 py-3 transition-all focus-within:bg-slate-200 dark:focus-within:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700">
                            <Input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder={currentConfig.placeholder}
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
                                    disabled={isLoading || !query.trim()}
                                    className={cn(
                                        "h-10 w-10 rounded-full transition-all",
                                        query.trim() ? "bg-[#692080] text-white hover:bg-[#501860]" : "text-slate-400 hover:bg-slate-200"
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
