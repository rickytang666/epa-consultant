import { cva, type VariantProps } from "class-variance-authority";
import Markdown from 'react-markdown';
import { cn } from "@/lib/utils";
import { User, Bot } from 'lucide-react';

const bubbleVariants = cva(
    "flex w-max max-w-[85%] flex-col gap-2 rounded-lg px-4 py-3 text-sm shadow-sm",
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

export interface MessageBubbleProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof bubbleVariants> {
    content: string;
    role: "user" | "assistant";
}

export function MessageBubble({ role, content, className, ...props }: MessageBubbleProps) {
    return (
        <div className={cn("flex items-start gap-3", role === "user" ? "justify-end" : "justify-start", "mb-4")}>
            {role === "assistant" && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 border">
                    <Bot className="h-4 w-4 text-primary" />
                </div>
            )}

            <div className={cn(bubbleVariants({ role }), "prose dark:prose-invert prose-sm max-w-none break-words", className)} {...props}>
                <Markdown>
                    {content}
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
