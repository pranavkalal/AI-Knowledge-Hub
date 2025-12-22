export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api";

export type PersonaType = "researcher" | "grower" | "extension_officer";

export interface AskRequest {
    question: string;
    k?: number;
    mode?: "dense" | "bm25" | "hybrid";
    rerank?: boolean;
    filters?: {
        year_min?: number;
        year_max?: number;
    };
    persona?: PersonaType;
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

// Library types
export interface LibraryDocument {
    title: string;
    year: number | null;
    project_code: string | null;
    author: string | null;
    publisher: string | null;
    date_issued: string | null;
    abstract: string | null;
    category: string | null;
    subject: string | null;
    pdf_url: string | null;
    source_page: string | null;
    filename: string | null;
}

export interface LibraryFilters {
    years: number[];
    subjects: string[];
    categories: string[];
}

export interface LibraryResponse {
    documents: LibraryDocument[];
    total: number;
    page: number;
    limit: number;
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

    // Library API
    library: {
        list: async (params?: {
            q?: string;
            year?: number;
            subject?: string;
            category?: string;
            page?: number;
            limit?: number;
        }): Promise<LibraryResponse> => {
            const searchParams = new URLSearchParams();
            if (params?.q) searchParams.set("q", params.q);
            if (params?.year) searchParams.set("year", params.year.toString());
            if (params?.subject) searchParams.set("subject", params.subject);
            if (params?.category) searchParams.set("category", params.category);
            if (params?.page) searchParams.set("page", params.page.toString());
            if (params?.limit) searchParams.set("limit", params.limit.toString());

            const response = await fetch(`${API_BASE}/library?${searchParams}`);
            if (!response.ok) {
                throw new Error(`API Error: ${response.statusText}`);
            }
            return response.json();
        },

        getFilters: async (): Promise<LibraryFilters> => {
            const response = await fetch(`${API_BASE}/library/filters`);
            if (!response.ok) {
                throw new Error(`API Error: ${response.statusText}`);
            }
            return response.json();
        },
    },
};

