const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function POST(req: Request) {
    try {
        const { messages, data } = await req.json();

        // Get the last user message
        const lastMessage = messages[messages.length - 1];
        if (!lastMessage || lastMessage.role !== 'user') {
            return new Response('No user message found', { status: 400 });
        }

        const persona = data?.persona || 'grower';
        const sessionId = data?.sessionId;

        // Call your FastAPI backend
        const response = await fetch(`${API_BASE}/api/ask?stream=true`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: lastMessage.content,
                persona,
                k: 5,
                mode: 'dense',
                rerank: true
            })
        });

        if (!response.ok) {
            throw new Error(`Backend returned ${response.status}`);
        }

        if (!response.body) {
            throw new Error('No response body from backend');
        }

        let citations: any[] = [];

        // Transform your SSE format to AI SDK format
        const stream = new ReadableStream({
            async start(controller) {
                const reader = response.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                try {
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            const trimmedLine = line.trim();
                            if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;

                            const dataStr = trimmedLine.slice(6);
                            if (dataStr === '[DONE]') continue;

                            try {
                                const data = JSON.parse(dataStr);

                                if (data.type === 'token') {
                                    // Stream the token directly (AI SDK expects plain text)
                                    controller.enqueue(new TextEncoder().encode(data.token));
                                } else if (data.type === 'sources') {
                                    // Store citations to append at the end
                                    citations = data.data;
                                } else if (data.type === 'error') {
                                    throw new Error(data.message);
                                }
                            } catch (e) {
                                console.warn('Failed to parse SSE message:', e);
                            }
                        }
                    }

                    // Append citations as metadata at the end
                    // We'll parse this in the frontend
                    if (citations.length > 0) {
                        const citationsJson = JSON.stringify(citations);
                        controller.enqueue(
                            new TextEncoder().encode(`\n\n<!--CITATIONS:${citationsJson}-->`)
                        );
                    }

                    controller.close();
                } catch (error) {
                    controller.error(error);
                }
            }
        });

        return new Response(stream, {
            headers: {
                'Content-Type': 'text/plain; charset=utf-8',
                'Transfer-Encoding': 'chunked'
            }
        });
    } catch (error: any) {
        console.error('Chat API error:', error);
        return new Response(
            JSON.stringify({ error: error.message || 'Internal server error' }),
            { status: 500, headers: { 'Content-Type': 'application/json' } }
        );
    }
}
