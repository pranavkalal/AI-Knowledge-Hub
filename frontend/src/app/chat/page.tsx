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
    interface ActiveDoc {
        docId: string;
        page?: number;
        bbox?: number[];
    }
    const [activeDoc, setActiveDoc] = useState<ActiveDoc | null>(null);

    const handleCitationClick = (docId: string, page?: number, bbox?: number[]) => {
        setActiveDoc({ docId, page, bbox });
    };

    return (
        <div className="relative flex h-[calc(100vh-3.5rem)] overflow-hidden">
            {/* Left Panel: Chat */}
            <div className={`flex flex-col bg-background transition-all duration-300 ${activeDoc ? "w-1/2 border-r" : "w-full max-w-5xl mx-auto"}`}>
                <ChatInterface initialQuery={initialQuery} onCitationClick={handleCitationClick} />
            </div>

            {/* Right Panel: PDF Viewer */}
            {activeDoc && (
                <div className="w-1/2 flex-1 bg-slate-100">
                    <DocumentViewer
                        docId={activeDoc.docId}
                        page={activeDoc.page}
                        bbox={activeDoc.bbox}
                        onClose={() => setActiveDoc(null)}
                    />
                </div>
            )}
        </div>
    );
}
