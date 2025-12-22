"use client";

import { ChatInterface } from "@/components/chat/chat-interface";
import { DocumentViewer } from "@/components/pdf/document-viewer";
import { useState, Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { PersonaType } from "@/lib/api";
import { useChatStore } from "@/lib/store";

function ChatContent() {
    const searchParams = useSearchParams();
    const initialQuery = searchParams.get("q") || "";
    const initialPersona = (searchParams.get("persona") as PersonaType) || "grower";
    const sessionId = searchParams.get("session");
    
    const { getSession, setActiveSession } = useChatStore();

    // Load existing session if provided
    useEffect(() => {
        if (sessionId) {
            setActiveSession(sessionId);
        }
    }, [sessionId, setActiveSession]);

    // Get existing session data
    const existingSession = sessionId ? getSession(sessionId) : undefined;

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
            <div className={`flex flex-col bg-background transition-all duration-300 ${activeDoc ? "w-1/2 border-r dark:border-slate-700" : "w-full max-w-5xl mx-auto"}`}>
                <ChatInterface 
                    initialQuery={initialQuery} 
                    initialPersona={existingSession?.persona || initialPersona} 
                    onCitationClick={handleCitationClick}
                    sessionId={sessionId || undefined}
                    existingMessages={existingSession?.messages}
                />
            </div>

            {/* Right Panel: PDF Viewer */}
            {activeDoc && (
                <div className="w-1/2 flex-1 bg-slate-100 dark:bg-slate-800">
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

export default function ChatPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center h-screen bg-background text-foreground">Loading...</div>}>
            <ChatContent />
        </Suspense>
    );
}

