import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Citation, PersonaType } from "./api";

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    error?: boolean;
    timestamp: number;
}

export interface ChatSession {
    id: string;
    title: string;
    messages: ChatMessage[];
    persona: PersonaType;
    createdAt: number;
    updatedAt: number;
}

interface ChatStore {
    sessions: ChatSession[];
    activeSessionId: string | null;
    
    // Actions
    createSession: (persona: PersonaType, firstMessage?: string) => string;
    addMessage: (sessionId: string, message: Omit<ChatMessage, "timestamp">) => void;
    updateMessage: (sessionId: string, messageId: string, updates: Partial<ChatMessage>) => void;
    setActiveSession: (sessionId: string | null) => void;
    deleteSession: (sessionId: string) => void;
    getSession: (sessionId: string) => ChatSession | undefined;
    getActiveSession: () => ChatSession | undefined;
    clearAllSessions: () => void;
}

export const useChatStore = create<ChatStore>()(
    persist(
        (set, get) => ({
            sessions: [],
            activeSessionId: null,

            createSession: (persona: PersonaType, firstMessage?: string) => {
                const id = `chat_${Date.now()}`;
                const title = firstMessage 
                    ? firstMessage.slice(0, 50) + (firstMessage.length > 50 ? "..." : "")
                    : "New Chat";
                const now = Date.now();
                
                const newSession: ChatSession = {
                    id,
                    title,
                    messages: [],
                    persona,
                    createdAt: now,
                    updatedAt: now,
                };

                set((state) => ({
                    sessions: [newSession, ...state.sessions],
                    activeSessionId: id,
                }));

                return id;
            },

            addMessage: (sessionId: string, message: Omit<ChatMessage, "timestamp">) => {
                const now = Date.now();
                set((state) => ({
                    sessions: state.sessions.map((session) =>
                        session.id === sessionId
                            ? {
                                ...session,
                                messages: [...session.messages, { ...message, timestamp: now }],
                                updatedAt: now,
                                // Update title from first user message if it was "New Chat"
                                title: session.title === "New Chat" && message.role === "user"
                                    ? message.content.slice(0, 50) + (message.content.length > 50 ? "..." : "")
                                    : session.title,
                            }
                            : session
                    ),
                }));
            },

            updateMessage: (sessionId: string, messageId: string, updates: Partial<ChatMessage>) => {
                set((state) => ({
                    sessions: state.sessions.map((session) =>
                        session.id === sessionId
                            ? {
                                ...session,
                                messages: session.messages.map((msg) =>
                                    msg.id === messageId ? { ...msg, ...updates } : msg
                                ),
                                updatedAt: Date.now(),
                            }
                            : session
                    ),
                }));
            },

            setActiveSession: (sessionId: string | null) => {
                set({ activeSessionId: sessionId });
            },

            deleteSession: (sessionId: string) => {
                set((state) => ({
                    sessions: state.sessions.filter((s) => s.id !== sessionId),
                    activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId,
                }));
            },

            getSession: (sessionId: string) => {
                return get().sessions.find((s) => s.id === sessionId);
            },

            getActiveSession: () => {
                const { sessions, activeSessionId } = get();
                return sessions.find((s) => s.id === activeSessionId);
            },

            clearAllSessions: () => {
                set({ sessions: [], activeSessionId: null });
            },
        }),
        {
            name: "chat-storage",
        }
    )
);



