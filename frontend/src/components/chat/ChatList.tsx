import { cn } from "@/lib/utils";
import { useChatScroll } from "@/hooks/useChatScroll";

interface Message {
    role: "user" | "assistant";
    content: string;
}

interface ChatListProps {
    messages: Message[];
}

export function ChatList({ messages }: ChatListProps) {
    const { scrollRef, onScroll } = useChatScroll(messages);

    return (
        <div
            ref={scrollRef}
            onScroll={onScroll}
            className="flex-1 overflow-y-auto p-4 space-y-4"
        >
            {messages.map((msg, i) => (
                <div
                    key={i}
                    className={cn(
                        "flex w-max max-w-[80%] flex-col gap-2 rounded-lg px-3 py-2 text-sm",
                        msg.role === "user"
                            ? "ml-auto bg-primary text-primary-foreground"
                            : "bg-muted"
                    )}
                >
                    {msg.content}
                </div>
            ))}
        </div>
    );
}
