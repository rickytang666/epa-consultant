"""
child deduplication cost benchmark: measure savings from filtering redundant summaries
"""

def estimate_tokens(text: str) -> int:
    """rough token estimation: ~4 chars per token"""
    return len(text) // 4


def calculate_uniqueness(preview_text: str, child_summary: str) -> float:
    """calculate what fraction of child summary words are unique (not in preview)"""
    preview_words = set(preview_text.lower().split())
    summary_words = set(child_summary.lower().split())
    
    if len(summary_words) == 0:
        return 0.0
    
    unique_words = summary_words - preview_words
    return len(unique_words) / len(summary_words)


def benchmark_child_deduplication():
    """measure token savings from filtering redundant child summaries"""
    
    print("=== child deduplication cost benchmark ===\n")
    
    # simulate parent section with children
    # format: (parent_preview, [(child_name, child_summary, uniqueness)])
    test_cases = [
        (
            "this section discusses data collection methods including sampling techniques and survey instruments",
            [
                ("sampling", "describes sampling techniques for data collection", 0.2),  # redundant
                ("instruments", "details the survey instruments and questionnaires used", 0.4),  # borderline
                ("validation", "explains cross-validation and reliability testing procedures", 0.8),  # unique
            ]
        ),
        (
            "results show significant improvements in model accuracy and performance metrics",
            [
                ("accuracy", "model accuracy improved significantly across all datasets", 0.1),  # very redundant
                ("latency", "inference latency reduced by 40% through optimization", 0.7),  # unique
                ("scalability", "system scales linearly up to 1000 concurrent users", 0.9),  # unique
            ]
        ),
        (
            "implementation uses python with tensorflow for deep learning models",
            [
                ("architecture", "neural network architecture with 5 convolutional layers", 0.6),  # somewhat unique
                ("training", "model training using tensorflow on gpu clusters", 0.3),  # redundant
                ("deployment", "containerized deployment with kubernetes and docker", 0.8),  # unique
            ]
        ),
    ]
    
    total_tokens_before = 0
    total_tokens_after = 0
    total_children_before = 0
    total_children_after = 0
    
    threshold = 0.3  # filter out children with < 30% unique words
    
    for i, (preview, children) in enumerate(test_cases, 1):
        print(f"parent section {i}:")
        print(f"  preview: \"{preview[:60]}...\"")
        print(f"  children:")
        
        section_tokens_before = 0
        section_tokens_after = 0
        
        for name, summary, uniqueness in children:
            tokens = estimate_tokens(summary)
            section_tokens_before += tokens
            total_children_before += 1
            
            keep = uniqueness >= threshold
            status = "✓ keep" if keep else "✗ filter"
            
            if keep:
                section_tokens_after += tokens
                total_children_after += 1
            
            print(f"    - {name}: {uniqueness:.1%} unique → {status} ({tokens} tokens)")
        
        savings = section_tokens_before - section_tokens_after
        savings_pct = (savings / section_tokens_before * 100) if section_tokens_before > 0 else 0
        
        print(f"  section savings: {savings} tokens ({savings_pct:.1f}%)")
        print()
        
        total_tokens_before += section_tokens_before
        total_tokens_after += section_tokens_after
    
    print("-" * 70)
    total_savings = total_tokens_before - total_tokens_after
    total_savings_pct = (total_savings / total_tokens_before * 100) if total_tokens_before > 0 else 0
    
    print(f"total children: {total_children_before} → {total_children_after} ({total_children_before - total_children_after} filtered)")
    print(f"total tokens: {total_tokens_before} → {total_tokens_after}")
    print(f"total savings: {total_savings} tokens ({total_savings_pct:.1f}%)")
    
    # cost calculation
    cost_before = (total_tokens_before / 1_000_000) * 0.25
    cost_after = (total_tokens_after / 1_000_000) * 0.25
    cost_savings = cost_before - cost_after
    
    print(f"\nestimated cost (gpt-5-mini):")
    print(f"  before filtering: ${cost_before:.6f}")
    print(f"  after filtering:  ${cost_after:.6f}")
    print(f"  savings:          ${cost_savings:.6f}")
    
    print(f"\nkey insight:")
    print(f"  - filters {total_children_before - total_children_after}/{total_children_before} redundant children")
    print(f"  - saves {total_savings_pct:.1f}% tokens on parent sections")
    print(f"  - preserves unique information (threshold: {threshold:.0%})")


if __name__ == "__main__":
    benchmark_child_deduplication()
