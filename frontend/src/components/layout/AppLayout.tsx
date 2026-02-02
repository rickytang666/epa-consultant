import { useState } from 'react';
import { useChat } from '@/hooks/useChat';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ChatLayout } from '@/components/chat/ChatLayout';
import { ContextPanel } from '@/components/pdf/ContextPanel';
import { TableExplorer } from '@/components/tables/TableExplorer';


export function AppLayout() {
    // rightPanel state: 'pdf' | 'tables' | null
    const [rightPanel, setRightPanel] = useState<'pdf' | 'tables' | null>(null);
    const [activeCitation, setActiveCitation] = useState<string | null>(null);

    const { messages, sendMessage, isLoading, sources } = useChat({
        onSourcesReceived: (newSources) => {
            if (newSources.length > 0 && rightPanel === null) {
                setRightPanel('pdf');
            }
        }
    });


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
                {/* RIGHT: Context (PDF) */}
                {rightPanel === 'pdf' && (
                    <>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize={50} minSize={30}>
                            <ContextPanel
                                sources={sources}
                                onClose={() => setRightPanel(null)}
                                activeCitation={activeCitation}
                                isLoading={isLoading}
                            />
                        </ResizablePanel>
                    </>
                )}
            </ResizablePanelGroup>
            
            {/* Full Screen Table Explorer with Slide-Over Transition */}
            <div
                className={`fixed inset-0 z-50 bg-background/80 backdrop-blur-sm transition-opacity duration-300 ${
                    rightPanel === 'tables' ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
                }`}
            >
                {/* The Sliding Layer */}
                <div
                    className={`absolute inset-y-0 right-0 w-full transform transition-transform duration-300 ease-in-out ${
                        rightPanel === 'tables' ? 'translate-x-0' : 'translate-x-full'
                    }`}
                >
                    {rightPanel === 'tables' && (
                         <div className="h-full w-full bg-background shadow-2xl animate-in slide-in-from-right duration-300 ease-out">
                            <TableExplorer onClose={() => setRightPanel(null)} />
                        </div>
                    )}
                </div>
            </div>
        </TooltipProvider>
    );
}
