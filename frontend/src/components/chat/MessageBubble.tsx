import { cva, type VariantProps } from "class-variance-authority";
import Markdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import { cn } from "@/lib/utils";
import { User, Bot } from 'lucide-react';

const bubbleVariants = cva(
    "flex w-fit max-w-[85%] flex-col gap-2 rounded-lg px-4 py-3 text-sm shadow-sm",
    {
        variants: {
            role: {
                user: "ml-auto bg-primary text-primary-foreground",
                assistant: "bg-muted/80 text-foreground border",
            },
        },
        defaultVariants: {
            role: "assistant",
        },
    }
);

import { CitationBadge } from "@/components/chat/CitationBadge";

export interface MessageBubbleProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof bubbleVariants> {
    content: string;
    role: "user" | "assistant";
    onCitationClick?: (citationKey: string) => void;
}

export function MessageBubble({ role, content, onCitationClick, className, ...props }: MessageBubbleProps) {
    // Pre-process content to turn [Source: ...] into a link we can intercept
    // Regex: Match [Source: <text>] or [source: <text>]
    // Replace with: [Source: <text>](#citation:<text>)
    // Regex matches:
    // 1. [Source: ...] or [source: ...]
    // 2. 【Source: ...】 or 【source: ...】
    // 3. (Source: ...) or (source: ...)
    const processedContent = content
        .replace(/<br\s*\/?>/gi, '\n') // Replace <br>, <br/>, <br /> with newline
        .replace(
            /(?:\[|【|\()[Ss]ource:\s*(.*?)(?:\]|】|\))/g,
            (_, capture) => {
                // encodeURIComponent doesn't encode parentheses, which breaks markdown links
                // if the citation contains unbalanced parentheses. We manually encode them.
                const encoded = encodeURIComponent(capture).replace(/\(/g, '%28').replace(/\)/g, '%29');
                return `[Source: ${capture}](#citation:${encoded})`;
            }
        );

    return (
        <div className={cn("flex items-start gap-3", role === "user" ? "justify-end" : "justify-start", "mb-4")}>
            {role === "assistant" && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 border">
                    <Bot className="h-4 w-4 text-primary" />
                </div>
            )}

            <div className={cn(bubbleVariants({ role }), "prose dark:prose-invert prose-sm max-w-none break-words prose-table:border prose-th:bg-muted prose-th:p-2 prose-td:p-2", className)} {...props}>
                <Markdown
                    remarkPlugins={[remarkBreaks, remarkGfm]}
                    components={{
                        a: ({ href, children, ...props }) => {
                            if (href?.startsWith('#citation:')) {
                                const rawKey = href.replace('#citation:', '');
                                const citationKey = decodeURIComponent(rawKey);
                                // If role is user, we shouldn't really have citations, but handle safely
                                return (
                                    <CitationBadge
                                        citationKey={citationKey}
                                        onClick={() => onCitationClick?.(citationKey)}
                                        className="no-underline align-middle"
                                    />
                                );
                            }
                            return <a href={href} {...props}>{children}</a>;
                        }
                    }}
                >
                    {processedContent}
                </Markdown>
            </div>

            {role === "user" && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted border">
                    <User className="h-4 w-4" />
                </div>
            )}
        </div>
    );
}
