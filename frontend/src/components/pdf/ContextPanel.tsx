import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

export function ContextPanel({ onClose }: { onClose: () => void }) {
    return (
        <div className="flex h-full flex-col border-l bg-muted/10">
            <header className="flex h-14 items-center border-b px-4">
                <h3 className="font-medium">Source Context</h3>
                <Button variant="ghost" size="icon" className="ml-auto" onClick={onClose}>
                    <X className="h-4 w-4" />
                </Button>
            </header>
            <div className="flex-1 p-4">
                {/* PDF Viewer */}
                <div className="text-sm text-muted-foreground">PDF Viewer will go here</div>
            </div>
        </div>
    );
}
