import { useMemo, useState, useEffect } from 'react';
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
    fileUrl?: string;
    citations: Citation[];
    activeCitation?: string | null;
    isLoading?: boolean;
}

export function PDFViewer({ fileUrl, citations, activeCitation, isLoading }: PDFViewerProps) {
    // Zoom State: Percentage (Default 100% = 700px)
    const [scalePercent, setScalePercent] = useState<number>(100);

    // Filter Logic: Get unique pages from citations
    const relevantPages = useMemo(() => {
        if (citations.length === 0) return [];
        const pages = citations.map(c => c.page).filter(p => p !== undefined && p !== null);
        return Array.from(new Set(pages)).sort((a, b) => a - b);
    }, [citations]);

    // Scroll to Active Citation Logic
    useEffect(() => {
        if (!activeCitation) return;
        console.log("[PDFViewer] Active Citation:", activeCitation);
        console.log("[PDFViewer] Citations:", citations);
        // Find the page number for this citation
        // We look for a source where the text matches activeCitation (which is the header path)
        // Correction: The backend sends [Source: Header > Path]. 
        // We need to match this against the citation's text or metadata? 
        // The `Citation` type has `text` (chunk text) and metadata.
        // It doesn't seem to store `header_path_str` in the top level `Citation` object in `types.ts`?
        // Checking `types.ts`... I recall `text`, `page`, `docId`. 
        // I might need to update `Citation` type to include `headerPath`.

        // Let's assume for now I will fix types.ts next. 
        // Fuzzy Matching Logic:
        // We check if the activeCitation (from LLM) is contained in the backend Header Path, or vice-versa.
        // Also check if it matches the text content directly (fallback).
        const match = citations.find(c => {
            // Normalize strings to handle non-breaking spaces and other artifacts
            const normalize = (str: string) => str.replace(/\s+/g, ' ').trim();

            const header = normalize(c.headerPath || "");
            const text = normalize(c.text || "");
            const needle = normalize(activeCitation);

            console.log("[PDFViewer] Header (Norm):", header);
            console.log("[PDFViewer] Needle (Norm):", needle);

            // Last Section Logic:
            // Extract the last part of the needle. If that fails, check the part before it.
            // Split by either '>' or '→', trim parts, filter empty
            const parts = needle.split(/[>→]/).map(p => p.trim()).filter(p => p);

            const lastPart = parts.length > 0 ? parts[parts.length - 1] : "";
            const secondLastPart = parts.length > 1 ? parts[parts.length - 2] : "";

            console.log("[PDFViewer] Parts:", parts);

            const isMatch = (
                header === needle ||
                header.includes(needle) ||
                (lastPart && header.includes(lastPart)) ||
                (secondLastPart && header.includes(secondLastPart)) ||
                text.includes(needle)
            );
            return isMatch;
        });

        console.log("[PDFViewer] Matched Citation:", match);
        const targetPage = match?.page;
        console.log("[PDFViewer] Target Page:", targetPage);

        if (targetPage) {
            const pageElement = document.getElementById(`pdf-page-${targetPage}`);
            console.log("[PDFViewer] Page Element found:", !!pageElement);
            if (pageElement) {
                pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        } else if (match && !targetPage) {
            // Match found but no page -> Text Only Source
            console.log("[PDFViewer] Jumping to Text Only sources");
            const unmappedElement = document.getElementById("unmapped-sources");
            if (unmappedElement) {
                unmappedElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        } else {
            console.warn("[PDFViewer] No matching page found for citation or page is undefined.");
        }
    }, [activeCitation, citations]);

    function onDocumentLoadSuccess() {
        // Placeholder for future use
    }

    // ... existing Custom Text Renderer ...
    function makeTextRenderer(pageNumber: number) {
        return (textItem: { str: string }) => {
            const str = textItem.str;
            
            // Defer highlighting until streaming finishes to avoid glitches
            if (isLoading) return str;

            const cleanStr = str.trim();
            
            // Noise Filter: Ignore short fragments unless they are numbers
            // This prevents highlighting single letters or short common words like "the"
            if (cleanStr.length < 4 && !/^\d+$/.test(cleanStr)) {
                return str;
            }

            const relevantCitations = citations.filter(c => c.page === pageNumber);

            const isMatch = relevantCitations.some(c =>
                c.text.includes(str) || (str.length > 5 && str.includes(c.text))
            );

            if (isMatch) {
                return `<mark class="bg-yellow-200 text-black rounded-sm px-0.5">${str}</mark>`;
            }
            return str;
        };
    }

    if (!fileUrl) {
        return <div className="p-4 text-center text-muted-foreground">No PDF loaded.</div>;
    }

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
                            <div
                                key={pageNum}
                                id={`pdf-page-${pageNum}`}
                                className="relative shadow-md bg-white transition-all duration-200"
                                style={{ width: currentWidth }}
                            >
                                {/* Badge */}
                                <div className="absolute top-2 right-2 z-10 bg-yellow-400 px-2 py-1 text-xs font-bold rounded text-white shadow-sm">
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

                {/* Unmapped Sources (No Page Number) */}
                {citations.filter(c => !c.page).length > 0 && (
                    <div id="unmapped-sources" className="mt-8 border-t pt-4">
                        <h4 className="mb-2 font-semibold text-gray-700 px-4">Other Sources (Text Only)</h4>
                        <div className="space-y-4 px-4 pb-8">
                            {citations.filter(c => !c.page).map((c, i) => (
                                <div key={i} className="rounded-lg border bg-white p-4 shadow-sm">
                                    <div className="mb-1 text-xs font-bold text-muted-foreground">
                                        {c.headerPath || "Unknown Source"}
                                    </div>
                                    <p className="text-sm text-gray-800">{c.text}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
