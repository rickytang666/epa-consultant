import { Badge } from "@/components/ui/badge";
import { FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface CitationBadgeProps {
    citationKey: string; // The path string e.g. "Header > Path"
    onClick?: () => void;
    className?: string;
}

export function CitationBadge({ citationKey, onClick, className }: CitationBadgeProps) {
    // Truncate long paths for display
    const label = citationKey.split('>').pop()?.trim() || citationKey;

    return (
        <Badge
            variant="secondary"
            className={cn(
                "inline-flex items-center gap-1 mx-1 cursor-pointer transition-colors hover:bg-purple-100 hover:text-purple-900 border-purple-200",
                className
            )}
            onClick={onClick}
            title={citationKey} // Full path on hover
        >
            <FileText className="h-3 w-3" />
            <span className="max-w-[150px] truncate">{label}</span>
        </Badge>
    );
}
