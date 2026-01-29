import { Button } from '@/components/ui/button';
import { ChatList } from '@/components/chat/ChatList';
import { BookOpen } from 'lucide-react';

interface ChatLayoutProps {
    onToggleContext: () => void;
    isContextOpen: boolean;
}

export function ChatLayout({ onToggleContext, isContextOpen }: ChatLayoutProps) {
    // Mock data for visual verification
    const messages = [
        { role: "assistant" as const, content: "Hello! I am your EPA Consultant. How can I help you today?" },
        { role: "user" as const, content: "Tell me about lead pipes." },
        { role: "assistant" as const, content: "The Lead and Copper Rule Improvements (LCRI) require water systems to identify and replace lead pipes..." }
    ];

    return (
        <div className="flex h-full flex-col">
            <header className="flex h-14 items-center border-b px-6">
                <h2 className="text-lg font-semibold">New Chat</h2>
                <div className="ml-auto">
                    <Button
                        variant={isContextOpen ? "secondary" : "outline"}
                        size="sm"
                        onClick={onToggleContext}
                        className="gap-2"
                    >
                        <BookOpen className="h-4 w-4" />
                        {isContextOpen ? "Hide References" : "Check References"}
                    </Button>
                </div>
            </header>
            <div className="flex-1 bg-background flex flex-col overflow-hidden">
                <ChatList messages={messages} />
                {/* Input placeholder */}
                <div className="p-4 border-t">
                    <div className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm text-muted-foreground">
                        Type your message...
                    </div>
                </div>
            </div>
        </div>
    );
}
