"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, AlertCircle, Sparkles } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_BASE, Citation } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

interface ChatInterfaceProps {
    initialQuery: string;
    onCitationClick: (docId: string) => void;
}

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    error?: boolean;
    isStreaming?: boolean;
}

export function ChatInterface({ initialQuery, onCitationClick }: ChatInterfaceProps) {
    const [query, setQuery] = useState(initialQuery);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const hasInitialized = useRef(false);
    const abortController = useRef<AbortController | null>(null);

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

        const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
        setMessages((prev) => [...prev, userMsg]);
        setQuery("");
        setIsLoading(true);

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
                    rerank: true
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
                const lines = buffer.split("\n\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.slice(6);
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
            }
        } catch (error: any) {
            if (error.name === 'AbortError') return;
            console.error("Chat Error:", error);
            setMessages((prev) => prev.map(msg =>
                msg.id === aiMsgId
                    ? { ...msg, content: "Sorry, I encountered an error connecting to the Knowledge Hub. Please try again.", error: true }
                    : msg
            ));
        } finally {
            setIsLoading(false);
            setMessages((prev) => prev.map(msg =>
                msg.id === aiMsgId ? { ...msg, isStreaming: false } : msg
            ));
            abortController.current = null;
        }
    };

    return (
        <div className="flex h-full flex-col bg-white relative">
            <ScrollArea className="flex-1 px-4 sm:px-0">
                <div className="flex flex-col space-y-8 pb-32 pt-20 max-w-3xl mx-auto">
                    <AnimatePresence initial={false}>
                        {messages.map((msg) => (
                            <motion.div
                                key={msg.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                {msg.role === "assistant" && (
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
                                        {msg.error ? <AlertCircle className="h-6 w-6 text-red-500" /> : <Sparkles className="h-6 w-6 text-[#4285f4] animate-pulse" />}
                                    </div>
                                )}

                                <div className={`flex max-w-[80%] flex-col gap-2 ${msg.role === "user"
                                    ? "bg-[#f0f4f9] text-slate-900 rounded-[20px] px-5 py-3"
                                    : "bg-transparent text-slate-900 px-0 py-0"
                                    }`}>
                                    <div className="prose prose-slate max-w-none leading-7 text-[16px]">
                                        {msg.content ? (
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        ) : (
                                            isLoading && msg.role === "assistant" && !msg.error && (
                                                <div className="flex items-center gap-1 h-6">
                                                    <span className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.3s]"></span>
                                                    <span className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.15s]"></span>
                                                    <span className="h-2 w-2 animate-bounce rounded-full bg-blue-400"></span>
                                                </div>
                                            )
                                        )}
                                    </div>

                                    {msg.citations && msg.citations.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mt-2">
                                            {msg.citations.map((cite, i) => (
                                                <motion.button
                                                    key={cite.sid}
                                                    whileHover={{ scale: 1.05 }}
                                                    whileTap={{ scale: 0.95 }}
                                                    onClick={() => onCitationClick(cite.doc_id)}
                                                    title={cite.doc_id}
                                                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:border-slate-300"
                                                >
                                                    <span className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center text-[10px] text-slate-500">{i + 1}</span>
                                                    <span className="truncate max-w-[150px]">{cite.doc_id}</span>
                                                </motion.button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                    <div ref={scrollRef} />
                </div>
            </ScrollArea>

            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pb-6 pt-10 px-4">
                <div className="max-w-3xl mx-auto">
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            handleSend(query);
                        }}
                        className="relative group"
                    >
                        <div className="relative flex items-center rounded-full bg-[#f0f4f9] px-4 py-3 transition-all focus-within:bg-[#e2e7eb] hover:bg-[#e2e7eb]">
                            <Input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Ask anything about cotton research..."
                                className="flex-1 border-none bg-transparent text-lg placeholder:text-slate-500 focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none h-auto py-1"
                            />
                            <div className="flex items-center space-x-2">
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
