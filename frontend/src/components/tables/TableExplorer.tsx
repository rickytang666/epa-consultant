import { useState, useEffect, useMemo } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Loader2, X, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Interface for raw incoming chunks
interface TableChunk {
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

// Interface for the merged table ready for display
interface GroupedTable {
  id: string;
  title: string;
  content: string;
  page_number: number;
  header_path: string;
  chunks_count: number;
  is_form: boolean;
}

interface TableExplorerProps {
  onClose: () => void;
}

export function TableExplorer({ onClose }: TableExplorerProps) {
  const [groupedTables, setGroupedTables] = useState<GroupedTable[]>([]);
  const [selectedTable, setSelectedTable] = useState<GroupedTable | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showForms, setShowForms] = useState(false);

  // Heuristic to detect if a table is likely just a blank form/worksheet
  const detectIsForm = (content: string): boolean => {
    // Remove markdown table syntax characters
    const cleanContent = content.replace(/[|\-\n\s]/g, "");
    // If there's very little actual alphanumeric content relative to the size, it's likely a form
    if (cleanContent.length < 20) return true;

    // Count empty cells vs filled cells (approximate)
    const lines = content.split("\n");
    let emptyCells = 0;
    let totalCells = 0;

    lines.forEach((line) => {
      if (!line.includes("|")) return;
      const cells = line.split("|").slice(1, -1); // content between pipes
      totalCells += cells.length;
      cells.forEach((cell) => {
        if (!cell.trim()) emptyCells++;
      });
    });

    // If > 70% of cells are empty, it's likely a form/worksheet
    return totalCells > 0 && emptyCells / totalCells > 0.7;
  };

  useEffect(() => {
    const fetchAndProcessTables = async () => {
      try {
        const response = await fetch("/api/tables");
        const data = await response.json();
        const rawChunks: TableChunk[] = data.tables || [];

        // 1. Group by table_id
        const groups: Record<string, TableChunk[]> = {};
        rawChunks.forEach((chunk) => {
          const tid = chunk.metadata.table_id;
          if (!groups[tid]) {
            groups[tid] = [];
          }
          groups[tid].push(chunk);
        });

        // 2. Process each group
        const processed: GroupedTable[] = Object.values(groups).map(
          (chunks) => {
            // Sort chunks naturally by chunk_id to ensure correct order
            // Assumes format like "chunk_003-t0", "chunk_003-t1", etc.
            chunks.sort((a, b) => {
              return a.chunk_id.localeCompare(b.chunk_id, undefined, {
                numeric: true,
                sensitivity: "base",
              });
            });

            const firstChunk = chunks[0];

            // Merge content
            // Keep full content of first chunk
            // For subsequent chunks, remove the first 2 lines (header + separator)
            const mergedContent = chunks
              .map((chunk, index) => {
                if (index === 0) return chunk.content;

                const lines = chunk.content.split("\n");
                // reliable check for markdown table header lines?
                // Usually starts with |
                if (lines.length > 2 && lines[1].trim().startsWith("|")) {
                  return lines.slice(2).join("\n");
                }
                return chunk.content;
              })
              .join("\n");

            // Check if headers contain "Form" or "Worksheet"
            const headerPathStr =
              firstChunk.header_path?.map((h) => h.name).join(" > ") ||
              "Table";
            const isFormHeuristic = detectIsForm(mergedContent);
            const hasFormKeyword = /form|worksheet|appendix/i.test(
              headerPathStr,
            );

            return {
              id: firstChunk.metadata.table_id,
              title:
                firstChunk.metadata.table_title ||
                `Table ${firstChunk.metadata.table_id}`,
              content: mergedContent,
              page_number: firstChunk.location.page_number,
              header_path: headerPathStr,
              chunks_count: chunks.length,
              is_form: isFormHeuristic || (hasFormKeyword && isFormHeuristic), // Stronger check: must look empty-ish
            };
          },
        );

        setGroupedTables(processed);

        // Select first visible table
        const visible = processed.filter((t) => !t.is_form);
        if (visible.length > 0) {
          setSelectedTable(visible[0]);
        } else if (processed.length > 0) {
          setSelectedTable(processed[0]);
        }
      } catch (error) {
        console.error("Failed to fetch tables:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAndProcessTables();
  }, []);

  const filteredTables = useMemo(() => {
    return groupedTables.filter((t) => showForms || !t.is_form);
  }, [groupedTables, showForms]);

  return (
    <div className="flex h-full flex-col border-l bg-background">
      <div className="flex h-14 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Table Explorer</h2>
          <Badge variant="outline" className="text-xs font-normal">
            {filteredTables.length} / {groupedTables.length}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant={showForms ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setShowForms(!showForms)}
            className="h-8 text-xs"
          >
            <Filter className="h-3 w-3 mr-1" />
            {showForms ? "Hide Forms" : "Show All"}
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
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
                {filteredTables.map((table) => (
                  <Button
                    key={table.id}
                    variant={
                      selectedTable?.id === table.id ? "secondary" : "ghost"
                    }
                    className="h-auto justify-start px-3 py-2 text-left"
                    onClick={() => setSelectedTable(table)}
                  >
                    <div className="flex flex-col gap-1 overflow-hidden">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          Page {table.page_number}
                        </span>
                        {table.is_form && (
                          <Badge
                            variant="secondary"
                            className="h-3 px-1 text-[9px]"
                          >
                            FORM
                          </Badge>
                        )}
                      </div>
                      <span className="truncate text-xs text-muted-foreground">
                        {table.header_path}
                      </span>
                      <span className="text-[10px] text-muted-foreground/50">
                        Merged {table.chunks_count} fragments
                      </span>
                    </div>
                  </Button>
                ))}
                {filteredTables.length === 0 && (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    No tables match filter.
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
                      <CardTitle className="flex items-center justify-between text-base font-medium">
                        <span>
                          Table Context (Page {selectedTable.page_number})
                        </span>
                        {selectedTable.is_form && (
                          <Badge variant="outline">Likely Form</Badge>
                        )}
                      </CardTitle>
                      <div className="mt-1 text-sm text-muted-foreground">
                        {selectedTable.header_path}
                      </div>
                    </CardHeader>
                    <CardContent className="pt-6 overflow-x-auto">
                      <div className="prose dark:prose-invert max-w-none prose-sm prose-table:border prose-td:p-2 prose-th:bg-muted prose-th:p-2 prose-table:w-full">
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
