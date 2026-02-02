import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { MessageSquare, Plus, PanelLeftOpen, PanelLeftClose } from "lucide-react";

interface SidebarProps {
    isCollapsed: boolean;
    onExpand?: () => void;
    onCollapse?: () => void;
}

export function Sidebar({ isCollapsed, onExpand, onCollapse }: SidebarProps) {
    return (
        <div
            data-testid="sidebar"
            className={cn(
                "flex h-full flex-col bg-muted/40 transition-all duration-300",
                isCollapsed ? "items-center p-2" : "p-4"
            )}
        >
            {/* Header / Logo Area */}
            <div className={cn("flex items-center", isCollapsed ? "justify-center" : "justify-between mb-4")}>
                {isCollapsed ? (
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onExpand} title="Expand Sidebar">
                        <PanelLeftOpen className="h-4 w-4" />
                    </Button>
                ) : (
                    <>
                        <div className="font-bold text-lg">EPA Consultant</div>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onCollapse} title="Collapse Sidebar">
                            <PanelLeftClose className="h-4 w-4" />
                        </Button>
                    </>
                )}
            </div>

            {/* New Chat Button */}
            <div className={cn("mb-4", isCollapsed && "flex justify-center")}>
                {isCollapsed ? (
                    <Button variant="outline" size="icon" className="h-8 w-8 rounded-full" title="New Chat">
                        <Plus className="h-4 w-4" />
                    </Button>
                ) : (
                    <Button className="w-full justify-start gap-2" variant="outline">
                        <Plus className="h-4 w-4" />
                        New Chat
                    </Button>
                )}
            </div>

            {/* History List */}
            {!isCollapsed && (
                <div className="flex-1 overflow-auto space-y-2">
                    <div className="text-xs font-medium text-muted-foreground px-2">Recent</div>
                    <Button variant="ghost" className="w-full justify-start text-sm font-normal truncate">
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Lead Pipe Rulings 2024
                    </Button>
                    <Button variant="ghost" className="w-full justify-start text-sm font-normal truncate">
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Forever Chemicals Limits
                    </Button>
                </div>
            )}
        </div>
    );
}
