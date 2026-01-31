"""
adaptive sampling cost benchmark: measure additional savings from depth-based budgets
"""

def estimate_tokens(text: str) -> int:
    """rough token estimation: ~4 chars per token"""
    return len(text) // 4


def benchmark_adaptive_sampling():
    """compare smart sampling vs adaptive sampling"""
    
    print("=== adaptive sampling cost benchmark ===\n")
    
    # simulate hierarchical document structure
    # format: (name, depth, has_children, content_length)
    sections = [
        ("introduction", 1, True, 3000),           # top-level with children
        ("  background", 2, False, 2000),          # mid-level leaf
        ("  scope", 2, False, 1500),               # mid-level leaf
        ("methods", 1, True, 5000),                # top-level with children
        ("  data collection", 2, True, 4000),      # mid-level with children
        ("    sampling", 3, False, 2500),          # deep section
        ("    instruments", 3, False, 1800),       # deep section
        ("  analysis", 2, True, 6000),             # mid-level with children
        ("    preprocessing", 3, True, 3000),      # deep with children
        ("      cleaning", 4, False, 2000),        # very deep leaf
        ("      normalization", 4, False, 1500),   # very deep leaf
        ("    modeling", 3, False, 4000),          # deep section
        ("results", 1, True, 8000),                # top-level with children
        ("  findings", 2, False, 5000),            # mid-level leaf
        ("  validation", 2, False, 3500),          # mid-level leaf
        ("conclusion", 1, False, 2500),            # top-level leaf
    ]
    
    total_tokens_smart = 0
    total_tokens_adaptive = 0
    
    print(f"{'section':<25} {'depth':<6} {'children':<9} {'length':<8} {'smart':<8} {'adaptive':<10} {'savings':<10}")
    print("-" * 95)
    
    for name, depth, has_children, length in sections:
        # smart sampling: fixed 3500 char budget
        smart_budget = 3500
        if length <= smart_budget:
            smart_preview = length
        else:
            smart_preview = smart_budget
        
        tokens_smart = estimate_tokens("x" * smart_preview)
        
        # adaptive sampling: depth-based budgets
        if depth >= 4:
            adaptive_budget = 2000
        elif has_children:
            adaptive_budget = 2500
        elif depth == 1:
            adaptive_budget = 4000
        else:
            adaptive_budget = 3500
        
        if length <= adaptive_budget:
            adaptive_preview = length
        else:
            adaptive_preview = adaptive_budget
        
        tokens_adaptive = estimate_tokens("x" * adaptive_preview)
        
        savings = tokens_smart - tokens_adaptive
        savings_pct = (savings / tokens_smart * 100) if tokens_smart > 0 else 0
        
        total_tokens_smart += tokens_smart
        total_tokens_adaptive += tokens_adaptive
        
        children_str = "yes" if has_children else "no"
        print(f"{name:<25} {depth:<6} {children_str:<9} {length:<8} {tokens_smart:<8} {tokens_adaptive:<10} {savings:>4} ({savings_pct:>5.1f}%)")
    
    print("-" * 95)
    total_savings = total_tokens_smart - total_tokens_adaptive
    total_savings_pct = (total_savings / total_tokens_smart * 100) if total_tokens_smart > 0 else 0
    
    print(f"{'TOTAL':<25} {'':<6} {'':<9} {'':<8} {total_tokens_smart:<8} {total_tokens_adaptive:<10} {total_savings:>4} ({total_savings_pct:>5.1f}%)")
    
    # cost calculation
    cost_smart = (total_tokens_smart / 1_000_000) * 0.25
    cost_adaptive = (total_tokens_adaptive / 1_000_000) * 0.25
    cost_savings = cost_smart - cost_adaptive
    
    print(f"\nestimated cost (gpt-5-mini):")
    print(f"  smart sampling:    ${cost_smart:.6f}")
    print(f"  adaptive sampling: ${cost_adaptive:.6f}")
    print(f"  savings:           ${cost_savings:.6f}")
    
    print(f"\nkey insights:")
    print(f"  - deep sections (depth >= 4): reduced from 3500 to 2000 chars")
    print(f"  - parent sections: reduced from 3500 to 2500 chars (rely on child summaries)")
    print(f"  - top-level sections: increased from 3500 to 4000 chars (more context)")
    print(f"  - net effect: {total_savings_pct:.1f}% additional savings beyond smart sampling")


if __name__ == "__main__":
    benchmark_adaptive_sampling()
