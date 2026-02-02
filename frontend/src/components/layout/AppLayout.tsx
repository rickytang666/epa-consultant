import { useState, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ChatLayout } from '@/components/chat/ChatLayout';
import { ContextPanel } from '@/components/pdf/ContextPanel';
import { TableExplorer } from '@/components/tables/TableExplorer';

interface AppLayoutProps {
    defaultLayout?: number[] | undefined;
}

export function AppLayout({ defaultLayout: _defaultLayout = [50, 50] }: AppLayoutProps) {
    // rightPanel state: 'pdf' | 'tables' | null
    const [rightPanel, setRightPanel] = useState<'pdf' | 'tables' | null>(null);
    const [activeCitation, setActiveCitation] = useState<string | null>(null);

    const { messages, sendMessage, isLoading, sources } = useChat();

    // Auto-open context panel (pdf) when sources arrive
    useEffect(() => {
        if (sources.length > 0 && rightPanel === null) setRightPanel('pdf');
    }, [sources]);

    const handleCitationClick = (citationKey: string) => {
        setRightPanel('pdf');
        setActiveCitation(citationKey);
    };

    return (
        <TooltipProvider delayDuration={0}>
            <ResizablePanelGroup
                orientation="horizontal"
                className="h-screen max-h-screen items-stretch"
            >
                {/* LEFT: Chat */}
                <ResizablePanel defaultSize={50} minSize={30} className="h-full">
                    <ChatLayout
                        messages={messages}
                        sendMessage={sendMessage}
                        isLoading={isLoading}
                        onToggleContext={() => setRightPanel(prev => prev === 'pdf' ? null : 'pdf')}
                        isContextOpen={rightPanel === 'pdf'}
                        onToggleTables={() => setRightPanel(prev => prev === 'tables' ? null : 'tables')}
                        isTablesOpen={rightPanel === 'tables'}
                        onCitationClick={handleCitationClick}
                    />
                </ResizablePanel>

                {/* RIGHT: Context (PDF) or Table Explorer */}
                {rightPanel !== null && (
                    <>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize={50} minSize={30}>
                            {rightPanel === 'pdf' ? (
                                <ContextPanel
                                    sources={sources}
                                    onClose={() => setRightPanel(null)}
                                    activeCitation={activeCitation}
                                    isLoading={isLoading}
                                />
                            ) : (
                                <TableExplorer
                                    onClose={() => setRightPanel(null)}
                                />
                            )}
                        </ResizablePanel>
                    </>
                )}
            </ResizablePanelGroup>
        </TooltipProvider>
    );
}
