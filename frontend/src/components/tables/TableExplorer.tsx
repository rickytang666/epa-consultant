import { useState, useEffect, useMemo } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Loader2, X, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

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
  header_path_raw?: { level: string; name: string }[];
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
              header_path_raw: firstChunk.header_path,
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
    <div className="flex h-full flex-col border-l shadow-xl bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between border-b px-4 bg-muted/20">
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
          {/* Left List: Minimal & Clear */}
          <div className="w-1/4 min-w-[250px] border-r bg-muted/30">
            <ScrollArea className="h-full">
              <div className="flex flex-col gap-1 p-2">
                {filteredTables.map((table) => (
                  <Button
                    key={table.id}
                    variant={
                      selectedTable?.id === table.id ? "secondary" : "ghost"
                    }
                    className={cn(
                      "h-auto justify-start px-3 py-3 text-left items-start whitespace-normal rounded-xl transition-all duration-200",
                      selectedTable?.id === table.id && "bg-accent shadow-sm border-l-4 border-l-primary rounded-l-none"
                    )}
                    onClick={() => setSelectedTable(table)}
                  >
                    <div className="flex flex-col gap-1 w-full">
                      <div className="flex items-start justify-between gap-2">
                        <span className={cn("font-medium text-sm line-clamp-2 break-words leading-tight", selectedTable?.id === table.id ? "text-foreground" : "text-muted-foreground")}>
                          {table.title}
                        </span>
                        {table.is_form && (
                          <Badge
                            variant="secondary"
                            className="h-3 px-1 text-[9px] shrink-0 mt-0.5 opacity-70"
                          >
                            FORM
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground mt-1.5 font-mono opacity-80">
                         <span>Page {table.page_number}</span>
                         <span className="text-[10px]">
                           {table.chunks_count > 1 ? `${table.chunks_count} frags` : ''}
                         </span>
                      </div>
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

          {/* Right Content: Expanded View with Tree Context */}
          <div className="flex-1 bg-background min-w-0 flex flex-col">
            {selectedTable ? (
              <div className="h-full w-full overflow-y-auto p-0">
                <div className="p-6 max-w-full">
                  <Card className="min-h-full border-0 shadow-none max-w-full">
                    <CardHeader className="pb-4 border-b max-w-full">
                      <div className="flex items-start justify-between gap-4">
                         <div className="min-w-0 flex-1 overflow-x-auto pb-2">
                           <CardTitle className="text-xl font-semibold leading-tight whitespace-nowrap">
                             {selectedTable.title}
                           </CardTitle>
                         </div>
                         <Badge variant="outline" className="text-sm shrink-0 mt-1">Page {selectedTable.page_number}</Badge>
                      </div>
                      
                      {/* Tree-like Header Context in Main Panel */}
                      <div className="mt-6 flex flex-col gap-2 overflow-x-auto">
                         <span className="text-xs font-medium text-muted-foreground/60 uppercase tracking-widest pl-1">Location Context</span>
                         <div className="flex flex-col gap-1.5 pl-1">
                          {selectedTable.header_path_raw ? (
                            selectedTable.header_path_raw.map((item, index) => (
                              <div key={index} className="flex items-center gap-3 whitespace-nowrap group">
                                <div className="flex flex-col items-center justify-center opacity-30 w-4">
                                   {index < selectedTable.header_path_raw!.length - 1 ? (
                                     <div className="w-[1px] h-full bg-foreground/50" />
                                   ) : (
                                     <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
                                   )}
                                </div>
                                <span
                                  className={cn(
                                    "text-sm transition-colors duration-200",
                                    index === selectedTable.header_path_raw!.length - 1
                                      ? "font-semibold text-foreground"
                                      : "text-muted-foreground group-hover:text-foreground/80"
                                  )}
                                >
                                  {item.name.replace(/\*\*/g, '')}
                                </span>
                              </div>
                            ))
                          ) : (
                            <span>{selectedTable.header_path}</span>
                          )}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-6 overflow-hidden max-w-full">
                      <div className="prose dark:prose-invert max-w-none prose-sm prose-table:border prose-td:p-3 prose-th:bg-muted prose-th:p-3 prose-table:w-full prose-table:shadow-sm overflow-x-auto pb-2">
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
              </div>
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
