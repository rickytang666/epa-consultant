import { useState, useRef, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { TooltipProvider } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Sidebar } from '@/components/layout/Sidebar';
import { ChatLayout } from '@/components/chat/ChatLayout';
import { ContextPanel } from '@/components/pdf/ContextPanel';
import { type PanelImperativeHandle } from "react-resizable-panels";

interface AppLayoutProps {
    defaultLayout?: number[] | undefined;
}

export function AppLayout({ defaultLayout: _defaultLayout = [20, 50, 30] }: AppLayoutProps) {
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [isContextOpen, setIsContextOpen] = useState(false);
    const [activeCitation, setActiveCitation] = useState<string | null>(null);
    const sidebarRef = useRef<PanelImperativeHandle>(null);

    const { messages, sendMessage, isLoading, sources } = useChat();

    // Auto-open context panel when sources arrive
    useEffect(() => {
        if (sources.length > 0) setIsContextOpen(true);
    }, [sources]);

    const handleCitationClick = (citationKey: string) => {
        setIsContextOpen(true);
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
                        onToggleContext={() => setIsContextOpen(prev => !prev)}
                        isContextOpen={isContextOpen}
                        onCitationClick={handleCitationClick}
                    />
                </ResizablePanel>

                {/* RIGHT: Context (PDF) */}
                {isContextOpen && (
                    <>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize="45" minSize="30" maxSize="80">
                            <ContextPanel
                                sources={sources}
                                onClose={() => setIsContextOpen(false)}
                                activeCitation={activeCitation}
                            />
                        </ResizablePanel>
                    </>
                )}
            </ResizablePanelGroup>
        </TooltipProvider>
    );
}
