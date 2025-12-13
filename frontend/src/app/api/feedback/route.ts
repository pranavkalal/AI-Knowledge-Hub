const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function POST(req: Request) {
    try {
        const feedback = await req.json();

        // Proxy to FastAPI backend
        const response = await fetch(`${API_BASE}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(feedback)
        });

        if (!response.ok) {
            throw new Error(`Backend returned ${response.status}`);
        }

        const data = await response.json();
        return Response.json(data);

    } catch (error: any) {
        console.error('Feedback API error:', error);
        return Response.json(
            { error: error.message || 'Failed to submit feedback' },
            { status: 500 }
        );
    }
}
