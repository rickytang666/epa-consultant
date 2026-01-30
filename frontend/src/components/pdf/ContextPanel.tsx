import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { PDFViewer } from "@/components/pdf/PDFViewer";
import type { Citation } from "@/types";

interface ContextPanelProps {
    sources: Citation[];
    onClose: () => void;
}

export function ContextPanel({ sources, onClose }: ContextPanelProps) {
    // For now, hardcode a sample PDF or use one if we have a real URL from sources?
    // Since we are running locally, we might need a test pdf in public/
    // Let's use a dummy online PDF or a local one if the user provided it.
    // Ideally, the source.docId maps to a URL. 
    // Assuming "/epa.pdf" exists in public for testing as per Plan.
    const fileUrl = "/epa.pdf";

    return (
        <div className="flex h-full flex-col border-l bg-background">
            <header className="flex h-14 items-center justify-between border-b px-4">
                <h3 className="font-semibold">Source Context</h3>
                <Button variant="ghost" size="icon" onClick={onClose}>
                    <X className="h-4 w-4" />
                </Button>
            </header>
            <div className="flex-1 overflow-hidden">
                <PDFViewer citations={sources} fileUrl={fileUrl} />
            </div>
        </div>
    );
}
