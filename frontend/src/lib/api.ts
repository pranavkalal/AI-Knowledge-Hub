export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api";

export interface AskRequest {
    question: string;
    k?: number;
    mode?: "dense" | "bm25" | "hybrid";
    rerank?: boolean;
    filters?: {
        year_min?: number;
        year_max?: number;
    };
}

export interface Citation {
    sid: string;
    doc_id: string;
    page?: number;
    bbox?: number[]; // [x, y, w, h] - Future proofing for Deep Linking
    text?: string;
    score?: number;  // Confidence score (0-1)
}

export interface AskResponse {
    answer: string;
    citations: Citation[];
}

export const api = {
    ask: async (payload: AskRequest): Promise<AskResponse> => {
        const response = await fetch(`${API_BASE}/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                k: 5,
                mode: "dense",
                rerank: true,
                ...payload,
            }),
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        return response.json();
    },
};
