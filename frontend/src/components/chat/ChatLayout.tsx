import { Button } from '@/components/ui/button';
import { ChatList } from '@/components/chat/ChatList';
import { ChatInput } from '@/components/chat/ChatInput';
import type { Message } from '@/types';
import { BookOpen, Table } from 'lucide-react';

interface ChatLayoutProps {
    messages: Message[];
    sendMessage: (content: string) => void;
    isLoading: boolean;
    onToggleContext: () => void;
    isContextOpen: boolean;
    onToggleTables: () => void;
    isTablesOpen: boolean;
    onCitationClick: (citationKey: string) => void;
}

export function ChatLayout({
    messages,
    sendMessage,
    isLoading,
    onToggleContext,
    isContextOpen,
    onToggleTables,
    isTablesOpen,
    onCitationClick
}: ChatLayoutProps) {


    return (
        <div className="flex h-full flex-col">
            <header className="flex h-14 items-center border-b px-6">
                <h2 className="text-lg font-semibold">EPA Consultant</h2>
                <div className="ml-auto flex gap-2">
                    <Button
                        variant={isTablesOpen ? "secondary" : "outline"}
                        size="sm"
                        onClick={onToggleTables}
                        className="gap-2"
                    >
                        <Table className="h-4 w-4" />
                        {isTablesOpen ? "Hide Tables" : "View Tables"}
                    </Button>
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
                <ChatList messages={messages} onCitationClick={onCitationClick} />
                <ChatInput onSend={sendMessage} isLoading={isLoading} />
            </div>
        </div>
    );
}
