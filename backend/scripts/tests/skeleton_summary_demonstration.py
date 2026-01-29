"""Script to test skeleton summary generation."""
import json
import sys
import os

import argparse
from scripts.tests.utils import load_or_extract_pdf

# Add backend directory to path
from data_processing.ingest import DocumentIngestor

def main():
    parser = argparse.ArgumentParser(description="Demonstrate skeleton summary generation.")
    parser.add_argument("file_path", help="Path to the PDF or JSON file to process.")
    parser.add_argument("--fix-headers", action="store_true", help="Enable header correction.")
    args = parser.parse_args()

    # Load data (auto-extracts if PDF)
    try:
        data = load_or_extract_pdf(args.file_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    markdown = data["markdown"]
    filename = os.path.basename(args.file_path)
    
    print(f"Loaded markdown data from {filename}.")
    print(f"Header Correction: {'Enabled' if args.fix_headers else 'Disabled'}")
    
    # Run the pipeline
    print("Running ingestion pipeline...")
    ingestor = DocumentIngestor(fix_headers=args.fix_headers)
    doc = ingestor.ingest(
        markdown_text=markdown, 
        filename=filename
    )
    
    print(f"Total pages: {doc.total_pages}")
    print(f"Merged Section Chunks (for summaries): {len(doc.section_chunks)}")
    print(f"Final RAG Chunks: {len(doc.chunks)}")
    
    # Generate Skeleton Summaries using the section_chunks
    print("=" * 60)
    print("GENERATING SKELETON SUMMARIES")
    print("=" * 60)
    
    summaries, summary_cost = ingestor.generate_skeleton_summaries_sync(doc.section_chunks)
    
    # Update doc costs for display/completeness
    doc.costs["skeleton_summaries"] = summary_cost
    doc.costs["total"] = doc.costs.get("header_correction", 0.0) + summary_cost
    
    print()
    print("=" * 60)
    print("SKELETON SUMMARIES GENERATED")
    print("=" * 60)
    
    sorted_keys = sorted(summaries.keys(), key=lambda k: (len(k), k))
    
    for key in sorted_keys:
        summary = summaries[key]
        if not key:
            section_name = "Document Root"
        else:
            section_name = " > ".join([h[1] for h in key])
            
        indent = "  " * (len(key))
        
        print()
        print(f"{indent}SECTION: {section_name}")
        print(f"{indent}SUMMARY:")
        # Indent the summary text slightly for better readability
        print(f"{indent}  {summary}")
        print("-" * 60)
    
    print()
    print("=" * 60)
    print(f"Total Cost: ${ingestor.total_cost:.6f}")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
