import { useChatScroll } from "@/hooks/useChatScroll";
import { MessageBubble } from "@/components/chat/MessageBubble";

interface Message {
    role: "user" | "assistant";
    content: string;
}

interface ChatListProps {
    messages: Message[];
    onCitationClick: (citationKey: string) => void;
}

export function ChatList({ messages, onCitationClick }: ChatListProps) {
    const { scrollRef, onScroll } = useChatScroll(messages);

    return (
        <div
            ref={scrollRef}
            onScroll={onScroll}
            data-testid="chat-list"
            className="flex-1 overflow-y-auto p-4"
        >
            {messages.map((msg, i) => (
                <MessageBubble
                    key={i}
                    role={msg.role}
                    content={msg.content}
                    onCitationClick={onCitationClick}
                />
            ))}
        </div>
    );
}
