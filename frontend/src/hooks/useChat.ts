import { useState, useCallback } from 'react';

interface Message {
    role: "user" | "assistant";
    content: string;
}

export function useChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const sendMessage = useCallback(async (content: string) => {
        // 1. Add user message immediately
        const userMsg: Message = { role: "user", content };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

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
                    }
                    // Explicitly IGNORE 'sources:' lines
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
        sendMessage,
        isLoading
    };
}
