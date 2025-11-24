"use client";

import { ChatInterface } from "@/components/chat/chat-interface";
import { DocumentViewer } from "@/components/pdf/document-viewer";
import { useState } from "react";
import { useSearchParams } from "next/navigation";

import Link from "next/link";

export default function ChatPage() {
    const searchParams = useSearchParams();
    const initialQuery = searchParams.get("q") || "";

    // State to manage the split view
    // In a real app, this might be in a global store (Zustand)
    const [activeDoc, setActiveDoc] = useState<string | null>(null);

    return (
        <div className="relative flex h-[calc(100vh-3.5rem)] overflow-hidden">
            {/* Top Logo Area */}
            <div className="absolute top-4 left-4 z-10">
                <Link href="/" className="block transition-opacity hover:opacity-80">
                    <img src="/logo.png" alt="CRDC Logo" className="h-8 w-auto object-contain" />
                </Link>
            </div>

            {/* Left Panel: Chat */}
            <div className={`flex flex-col bg-background transition-all duration-300 ${activeDoc ? "w-1/2 border-r" : "w-full max-w-5xl mx-auto"}`}>
                <ChatInterface initialQuery={initialQuery} onCitationClick={setActiveDoc} />
            </div>

            {/* Right Panel: PDF Viewer */}
            {activeDoc && (
                <div className="w-1/2 flex-1 bg-slate-100">
                    <DocumentViewer docId={activeDoc} onClose={() => setActiveDoc(null)} />
                </div>
            )}
        </div>
    );
}
