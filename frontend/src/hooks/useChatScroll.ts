import { useEffect, useRef } from 'react';

export function useChatScroll<T>(dep: T) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // 1. Check if we should auto-scroll BEFORE the update
    const isAtBottomRef = useRef(true);

    const onScroll = () => {
        const node = scrollRef.current;
        if (!node) return;

        const { scrollTop, scrollHeight, clientHeight } = node;
        // Tolerance of 50px
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
        isAtBottomRef.current = isAtBottom;
    };

    // 2. Perform scroll AFTER the update (dependency change)
    useEffect(() => {
        if (isAtBottomRef.current) {
            scrollRef.current?.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: 'smooth'
            });
        }
    }, [dep]);

    return { scrollRef, onScroll };
}
