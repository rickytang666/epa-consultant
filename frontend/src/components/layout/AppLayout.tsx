import { useState, useRef, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { TooltipProvider } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Sidebar } from '@/components/layout/Sidebar';
import { ChatLayout } from '@/components/chat/ChatLayout';
import { ContextPanel } from '@/components/pdf/ContextPanel';
import { TableExplorer } from '@/components/tables/TableExplorer';
import { type PanelImperativeHandle } from "react-resizable-panels";

interface AppLayoutProps {
    defaultLayout?: number[] | undefined;
}

export function AppLayout({ defaultLayout: _defaultLayout = [20, 50, 30] }: AppLayoutProps) {
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    // rightPanel state: 'pdf' | 'tables' | null
    const [rightPanel, setRightPanel] = useState<'pdf' | 'tables' | null>(null);
    const [activeCitation, setActiveCitation] = useState<string | null>(null);
    const sidebarRef = useRef<PanelImperativeHandle>(null);

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
                {/* LEFT: Sidebar */}
                <ResizablePanel
                    panelRef={sidebarRef}
                    defaultSize="25"
                    collapsedSize={50}
                    collapsible={true}
                    minSize="20"
                    maxSize="25"
                    onResize={(data) => {
                        const isCollapsed = data.inPixels < 80; // slightly larger threshold than collapsedSize
                        setIsSidebarCollapsed(isCollapsed);
                    }}
                    className={cn(
                        isSidebarCollapsed && "min-w-[50px] transition-all duration-300 ease-in-out"
                    )}
                >
                    <Sidebar
                        isCollapsed={isSidebarCollapsed}
                        onExpand={() => sidebarRef.current?.resize("25")}
                        onCollapse={() => sidebarRef.current?.collapse()}
                    />
                </ResizablePanel>

                <ResizableHandle withHandle />

                {/* MIDDLE: Chat */}
                <ResizablePanel defaultSize="35" minSize="30" className="h-full">
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
                        <ResizablePanel defaultSize="45" minSize="30" maxSize="80">
                            {rightPanel === 'pdf' ? (
                                <ContextPanel
                                    sources={sources}
                                    onClose={() => setRightPanel(null)}
                                    activeCitation={activeCitation}
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
