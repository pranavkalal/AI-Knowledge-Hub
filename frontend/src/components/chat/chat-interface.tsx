"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, AlertCircle, Sparkles } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_BASE, Citation } from "@/lib/api";
import ReactMarkdown from "react-markdown";

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

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, isLoading]);

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
        <div className="flex h-full flex-col bg-slate-50/50 dark:bg-slate-900/50 backdrop-blur-sm">
            <div className="flex items-center justify-center p-4 border-b border-slate-200/50 bg-white/50 backdrop-blur-md">
                <img src="/logo.png" alt="CRDC Logo" className="h-12 w-auto object-contain" />
            </div>
            <ScrollArea className="flex-1 p-4 sm:p-6">
                <div className="space-y-6 pb-4 max-w-5xl mx-auto">
                    <AnimatePresence initial={false}>
                        {messages.map((msg) => (
                            <motion.div
                                key={msg.id}
                                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                            >
                                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full shadow-sm ${msg.role === "user"
                                        ? "bg-slate-200 text-slate-600"
                                        : msg.error
                                            ? "bg-red-100 text-red-600"
                                            : "bg-[#692080] text-white"
                                    }`}>
                                    {msg.role === "user" ? <User className="h-5 w-5" /> : msg.error ? <AlertCircle className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
                                </div>

                                <div className={`flex max-w-[85%] flex-col gap-2 rounded-2xl p-5 shadow-sm ${msg.role === "user"
                                        ? "bg-white text-slate-800 ml-12"
                                        : "glass text-slate-800 mr-12"
                                    }`}>
                                    <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed break-words">
                                        {msg.content ? (
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        ) : (
                                            isLoading && msg.role === "assistant" && !msg.error && (
                                                <div className="flex items-center gap-2 text-slate-400">
                                                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#692080] [animation-delay:-0.3s]"></span>
                                                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#692080] [animation-delay:-0.15s]"></span>
                                                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#692080]"></span>
                                                </div>
                                            )
                                        )}
                                    </div>

                                    {msg.citations && msg.citations.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-black/5 dark:border-white/10">
                                            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider flex items-center gap-1">
                                                <Bot className="h-3 w-3" /> Sources
                                            </span>
                                            {msg.citations.map((cite, i) => (
                                                <motion.button
                                                    key={cite.sid}
                                                    whileHover={{ scale: 1.05 }}
                                                    whileTap={{ scale: 0.95 }}
                                                    onClick={() => onCitationClick(cite.doc_id)}
                                                    title={cite.doc_id}
                                                    className="inline-flex items-center gap-1 rounded-full border border-purple-100 bg-purple-50/50 px-2.5 py-1 text-xs font-medium text-purple-700 transition-colors hover:bg-purple-100 hover:border-purple-200"
                                                >
                                                    <span className="w-4 h-4 rounded-full bg-purple-200 flex items-center justify-center text-[10px]">{i + 1}</span>
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

            <div className="p-4 sm:p-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-t border-slate-200/50">
                <div className="max-w-5xl mx-auto relative">
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            handleSend(query);
                        }}
                        className="relative group"
                    >
                        <Input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Ask anything about cotton research..."
                            className="pr-14 h-14 text-base rounded-full border-slate-200 bg-white shadow-sm transition-all focus:ring-2 focus:ring-[#692080]/20 focus:border-[#692080] pl-6"
                        />
                        <Button
                            type="submit"
                            size="icon"
                            disabled={isLoading || !query.trim()}
                            className={`absolute right-2 top-2 h-10 w-10 rounded-full transition-all duration-300 ${query.trim()
                                    ? "bg-[#692080] hover:bg-[#501860] hover:shadow-lg hover:shadow-[#692080]/30"
                                    : "bg-slate-200 text-slate-400"
                                }`}
                        >
                            <Send className="h-5 w-5" />
                        </Button>
                    </form>
                    <div className="text-center mt-2">
                        <span className="text-[10px] text-slate-400 font-medium">AI Knowledge Hub • Powered by RAG</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
