import { useState, useCallback } from 'react';
import type { Message, SourceChunk, Citation } from '../types';


export function useChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    // State for sources (citations)
    const [sources, setSources] = useState<Citation[]>([]);

    const sendMessage = useCallback(async (content: string) => {
        // 1. Add user message immediately
        const userMsg: Message = { role: "user", content };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);
        setSources([]); // Reset sources for new query

        try {
            // 2. Prepare assistant message placeholder
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);

            const response = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: content }),
            });

            if (!response.ok) throw new Error('Network response was not ok');
            if (!response.body) throw new Error('No response body');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = "";
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                // Split by newline
                const lines = buffer.split('\n');

                // Keep the last part in buffer (it might be incomplete)
                buffer = lines.pop() || "";

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (trimmedLine.startsWith('content: ')) {
                        // Extract content payload
                        const text = trimmedLine.slice(9); // remove "content: "
                        assistantMessage += text;

                        // Update the last message (assistant) with new token
                        setMessages(prev => {
                            const newHistory = [...prev];
                            const lastMsg = newHistory[newHistory.length - 1];
                            if (lastMsg.role === 'assistant') {
                                lastMsg.content = assistantMessage;
                            }
                            return newHistory;
                        });
                    } else if (trimmedLine.startsWith('sources: ')) {
                        // Extract and parse sources payload
                        try {
                            const jsonStr = trimmedLine.slice(9);
                            const rawSources = JSON.parse(jsonStr) as SourceChunk[];
                            // Map to frontend Citation model
                            const citations: Citation[] = rawSources.map(s => ({
                                id: s.chunk_id,
                                text: s.text,
                                page: s.metadata.page_number,
                                docId: s.metadata.document_id
                            }));

                            setSources(citations);
                        } catch (e) {
                            console.error("Failed to parse sources:", e);
                        }
                    }
                }
            }

        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => [...prev, { role: "assistant", content: "**Error:** Failed to get response." }]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    return {
        messages,
        sources,
        sendMessage,
        isLoading
    };

}
