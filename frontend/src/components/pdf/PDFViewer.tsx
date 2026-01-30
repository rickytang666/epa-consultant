import { useMemo, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import type { Citation } from '../../types';
import { Slider } from '@/components/ui/slider';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Worker setup for Vite
// Usually we copy the worker to public or use a CDN. For simplicity in dev:
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
).toString();

interface PDFViewerProps {
    fileUrl?: string; // We might need to fetch the blob or just use a static test file for now
    citations: Citation[];
}

export function PDFViewer({ fileUrl, citations }: PDFViewerProps) {
    // Zoom State: Percentage (Default 100% = 700px)
    const [scalePercent, setScalePercent] = useState<number>(100);

    // Filter Logic: Get unique pages from citations
    const relevantPages = useMemo(() => {
        if (citations.length === 0) return [];
        const pages = citations.map(c => c.page).filter(p => p !== undefined && p !== null);
        return Array.from(new Set(pages)).sort((a, b) => a - b);
    }, [citations]);

    function onDocumentLoadSuccess() {
        // Placeholder for future use
    }

    // Highlighting Logic: Custom Text Renderer
    function makeTextRenderer(pageNumber: number) {
        return (textItem: any) => {
            const str = textItem.str;

            // Find if this string matches any citation text for this page
            const relevantCitations = citations.filter(c => c.page === pageNumber);

            // Check if ANY source text contains this string (or vice versa)
            // We use a loose match to handle fragmentation:
            // 1. source.includes(str) -> The text item is part of the source (e.g. "Agency" in "EPA Agency")
            // 2. str.includes(source) -> The text item contains the source (e.g. "The EPA Agency" contains "EPA")
            const isMatch = relevantCitations.some(c =>
                c.text.includes(str) || (str.length > 5 && str.includes(c.text))
            );

            if (isMatch) {
                // Return highlighted markup
                return `<mark class="bg-yellow-200 text-black rounded-sm px-0.5">${str}</mark>`;
            }

            return str;
        };
    }

    // Fallback if no file
    if (!fileUrl) {
        return <div className="p-4 text-center text-muted-foreground">No PDF loaded.</div>;
    }

    // Calculate dynamic width based on scale (Base 700px)
    const currentWidth = 700 * (scalePercent / 100);

    return (
        <div className="flex h-full w-full flex-col bg-gray-100">
            {/* Toolbar */}
            <div className="flex items-center justify-between border-b bg-white px-4 py-2 sticky top-0 z-20 shadow-sm">
                <span className="text-sm font-medium text-gray-700">Zoom: {scalePercent}%</span>
                <Slider
                    value={[scalePercent]}
                    onValueChange={(val: number[]) => setScalePercent(val[0])}
                    min={50}
                    max={200}
                    step={10}
                    className="w-32"
                />
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-4 w-full">
                <Document
                    file={fileUrl}
                    onLoadSuccess={onDocumentLoadSuccess}
                    className="flex flex-col items-center gap-4"
                >
                    {relevantPages.length > 0 ? (
                        relevantPages.map(pageNum => (
                            <div key={pageNum} className="relative shadow-md border-2 border-yellow-400 bg-white transition-all duration-200" style={{ width: currentWidth }}>
                                {/* Badge */}
                                <div className="absolute top-2 right-2 z-10 bg-yellow-400 px-2 py-1 text-xs font-bold rounded text-black shadow-sm">
                                    Page {pageNum} (Relevant)
                                </div>
                                <Page
                                    pageNumber={pageNum}
                                    width={currentWidth}
                                    renderTextLayer={true}
                                    renderAnnotationLayer={false}
                                    customTextRenderer={makeTextRenderer(pageNum)}
                                />
                            </div>
                        ))
                    ) : (
                        <div className="text-sm text-center text-gray-500 mt-10">
                            No specific citations found for this query.
                        </div>
                    )}
                </Document>
            </div>
        </div>
    );
}
