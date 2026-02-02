import { useState, useEffect } from 'react';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { cn } from "@/lib/utils";
import { Loader2, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface TableData {
    chunk_id: string;
    document_id: string;
    content: string;
    chunk_index: number;
    location: {
        page_number: number;
    };
    header_path?: { level: string; name: string }[];
    metadata: {
        is_table: true;
        table_id: string;
        table_title: string;
    };
}

interface TableExplorerProps {
    onClose: () => void;
}

export function TableExplorer({ onClose }: TableExplorerProps) {
    const [tables, setTables] = useState<TableData[]>([]);
    const [selectedTable, setSelectedTable] = useState<TableData | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchTables = async () => {
            try {
                const response = await fetch('/api/tables');
                const data = await response.json();
                setTables(data.tables || []);
                // Select first table by default if available
                if (data.tables && data.tables.length > 0) {
                    setSelectedTable(data.tables[0]);
                }
            } catch (error) {
                console.error("Failed to fetch tables:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchTables();
    }, []);

    return (
        <div className="flex h-full flex-col border-l bg-background">
            <div className="flex h-14 items-center justify-between border-b px-4">
                <h2 className="text-lg font-semibold">Table Explorer</h2>
                <Button variant="ghost" size="icon" onClick={onClose}>
                    <X className="h-4 w-4" />
                </Button>
            </div>

            {isLoading ? (
                <div className="flex flex-1 items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
            ) : (
                <div className="flex flex-1 overflow-hidden">
                    {/* Left List */}
                    <div className="w-1/3 border-r bg-muted/30">
                        <ScrollArea className="h-full">
                            <div className="flex flex-col gap-1 p-2">
                                {tables.map((table) => (
                                    <Button
                                        key={table.metadata.table_id}
                                        variant={selectedTable?.metadata.table_id === table.metadata.table_id ? "secondary" : "ghost"}
                                        className="h-auto justify-start px-3 py-2 text-left"
                                        onClick={() => setSelectedTable(table)}
                                    >
                                        <div className="flex flex-col gap-1 overflow-hidden">
                                            <span className="font-medium">
                                                Page {table.location.page_number}
                                            </span>
                                            <span className="truncate text-xs text-muted-foreground">
                                                {table.header_path?.map(h => h.name).join(" > ") || "Table"}
                                            </span>
                                        </div>
                                    </Button>
                                ))}
                                {tables.length === 0 && (
                                    <div className="p-4 text-center text-sm text-muted-foreground">
                                        No tables found.
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* Right Content */}
                    <div className="flex-1 bg-background">
                        {selectedTable ? (
                            <ScrollArea className="h-full">
                                <div className="p-6">
                                    <Card>
                                        <CardHeader className="pb-3 border-b bg-muted/10">
                                            <CardTitle className="text-base font-medium flex justify-between items-center">
                                                <span>Table Context (Page {selectedTable.location.page_number})</span>
                                            </CardTitle>
                                            <div className="text-sm text-muted-foreground mt-1">
                                                {selectedTable.header_path?.map(h => h.name).join(" > ")}
                                            </div>
                                        </CardHeader>
                                        <CardContent className="pt-6 overflow-x-auto">
                                            <div className="prose dark:prose-invert max-w-none prose-sm prose-table:border prose-th:bg-muted prose-th:p-2 prose-td:p-2 prose-table:w-full">
                                                <Markdown
                                                    remarkPlugins={[remarkGfm]}
                                                    rehypePlugins={[rehypeRaw]}
                                                >
                                                    {selectedTable.content}
                                                </Markdown>
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>
                            </ScrollArea>
                        ) : (
                            <div className="flex h-full items-center justify-center text-muted-foreground">
                                Select a table to view
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
