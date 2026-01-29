import { useState, useRef } from 'react';
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
    const sidebarRef = useRef<PanelImperativeHandle>(null);

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
                <ResizablePanel defaultSize="45" minSize="35" className="h-full">
                    <ChatLayout
                        onToggleContext={() => setIsContextOpen(prev => !prev)}
                        isContextOpen={isContextOpen}
                    />
                </ResizablePanel>

                {/* RIGHT: Context (PDF) */}
                {isContextOpen && (
                    <>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize="35" minSize="25" maxSize="75">
                            <ContextPanel onClose={() => setIsContextOpen(false)} />
                        </ResizablePanel>
                    </>
                )}
            </ResizablePanelGroup>
        </TooltipProvider>
    );
}
