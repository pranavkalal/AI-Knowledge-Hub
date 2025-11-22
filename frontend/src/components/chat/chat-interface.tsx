"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, AlertCircle } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { api, Citation } from "@/lib/api";

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
}

export function ChatInterface({ initialQuery, onCitationClick }: ChatInterfaceProps) {
    const [query, setQuery] = useState(initialQuery);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const hasInitialized = useRef(false);

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
            citations: []
        };
        setMessages((prev) => [...prev, aiMsg]);

        try {
            // Use streaming API if available, otherwise fallback to normal
            // For now, we'll simulate streaming or use the normal API and update the message
            const response = await api.ask({ question: text });

            setMessages((prev) => prev.map(msg =>
                msg.id === aiMsgId
                    ? { ...msg, content: response.answer, citations: response.citations }
                    : msg
            ));
        } catch (error) {
            console.error("Chat Error:", error);
            setMessages((prev) => prev.map(msg =>
                msg.id === aiMsgId
                    ? { ...msg, content: "Sorry, I encountered an error connecting to the Knowledge Hub. Please try again.", error: true }
                    : msg
            ));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex h-full flex-col">
            <ScrollArea className="flex-1 p-4">
                <div className="space-y-6 pb-4">
                    {messages.map((msg) => (
                        <motion.div
                            key={msg.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                        >
                            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${msg.role === "user" ? "bg-slate-200" : msg.error ? "bg-red-500 text-white" : "bg-[#009B77] text-white"}`}>
                                {msg.role === "user" ? <User className="h-5 w-5" /> : msg.error ? <AlertCircle className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                            </div>
                            <div className={`flex max-w-[80%] flex-col gap-2 rounded-lg p-4 text-sm ${msg.role === "user" ? "bg-slate-100" : "bg-white border border-slate-100 shadow-sm"}`}>
                                <div className="prose prose-sm dark:prose-invert whitespace-pre-wrap">
                                    {msg.content || (isLoading && msg.role === "assistant" && !msg.error ? <span className="animate-pulse">Thinking...</span> : "")}
                                </div>
                                {msg.citations && msg.citations.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-slate-100">
                                        <span className="text-xs text-slate-400 font-medium">Sources:</span>
                                        {msg.citations.map((cite, i) => (
                                            <button
                                                key={cite.sid}
                                                onClick={() => onCitationClick(cite.doc_id)}
                                                title={cite.doc_id}
                                                className="inline-flex items-center rounded-full border border-transparent bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 transition-colors hover:bg-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                                            >
                                                [{i + 1}]
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    ))}
                    <div ref={scrollRef} />
                </div>
            </ScrollArea>
            <div className="border-t p-4 bg-white">
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        handleSend(query);
                    }}
                    className="relative"
                >
                    <Input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Ask a follow-up question..."
                        className="pr-12 h-12 text-base"
                    />
                    <Button
                        type="submit"
                        size="icon"
                        disabled={isLoading || !query.trim()}
                        className="absolute right-2 top-2 h-8 w-8 bg-[#009B77] hover:bg-[#007a5e]"
                    >
                        <Send className="h-4 w-4" />
                    </Button>
                </form>
            </div>
        </div>
    );
}
