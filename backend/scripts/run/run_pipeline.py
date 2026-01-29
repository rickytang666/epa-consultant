#!/usr/bin/env python
"""
End-to-end pipeline: PDF → Markdown → Processed Chunks
Combines extraction and parsing into a single command.
"""

import os
import sys
import argparse
import json
from dotenv import load_dotenv

# Ensure backend modules are found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from data_processing.pdf_extractor import extract_pdf_sync
from data_processing.ingest import DocumentIngestor

load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="End-to-end pipeline: Extract PDF and process into RAG chunks."
    )
    parser.add_argument("pdf_path", help="Path to PDF file to process")
    parser.add_argument("--fix-headers", action="store_true", help="Enable header correction LLM step")
    parser.add_argument("--skip-summaries", action="store_true", default=True, help="Skip summary generation (default: True for MVP)")
    parser.add_argument("--output-dir", default="data/processed", help="Output directory for processed JSON")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)

    filename = os.path.basename(args.pdf_path)
    print(f"\n{'='*60}")
    print(f"Processing: {filename}")
    print(f"{'='*60}\n")

    # Step 1: Extract PDF to markdown
    print("Step 1/2: Extracting PDF to markdown...")
    try:
        result = extract_pdf_sync(args.pdf_path)
        markdown = result.get("markdown", "")
        if not markdown:
            print("Error: No markdown content extracted from PDF")
            sys.exit(1)
        print(f"✓ Extracted {len(markdown)} characters of markdown\n")
    except Exception as e:
        print(f"Error during PDF extraction: {e}")
        sys.exit(1)

    # Step 2: Process markdown into chunks
    print("Step 2/2: Processing markdown into RAG chunks...")
    try:
        ingestor = DocumentIngestor(fix_headers=args.fix_headers)
        doc = ingestor.ingest(markdown, filename=filename)
        
        # Generate summaries if requested
        if not args.skip_summaries:
            print("  → Generating skeleton summaries...")
            summaries, sum_cost = ingestor.generate_skeleton_summaries_sync(doc.chunks)
            doc.section_summaries = summaries
            
            print("  → Generating document summary...")
            doc_summary, doc_cost = ingestor.generate_document_summary(summaries, filename)
            doc.document_summary = doc_summary
            
            doc.costs["skeleton_summaries"] = sum_cost
            doc.costs["document_summary"] = doc_cost
            doc.costs["total"] = doc.costs.get("header_correction", 0.0) + sum_cost + doc_cost
        
        print(f"✓ Processed into {len(doc.chunks)} chunks\n")
    except Exception as e:
        print(f"Error during processing: {e}")
        sys.exit(1)

    # Step 3: Save output
    os.makedirs(args.output_dir, exist_ok=True)
    output_filename = filename.replace(".pdf", ".json")
    output_path = os.path.join(args.output_dir, output_filename)
    
    try:
        with open(output_path, "w") as f:
            json.dump(doc.model_dump(), f, indent=2, default=str)
        print(f"{'='*60}")
        print(f"✓ SUCCESS: Saved to {output_path}")
        print(f"{'='*60}\n")
        
        # Summary
        print("Summary:")
        print(f"  Document ID: {doc.document_id}")
        print(f"  Chunks: {len(doc.chunks)}")
        print(f"  Header Correction: {'Enabled' if args.fix_headers else 'Disabled'}")
        print(f"  Summaries: {'Generated' if not args.skip_summaries else 'Skipped'}")
        if doc.costs.get("total", 0) > 0:
            print(f"  Total Cost: ${doc.costs['total']:.6f}")
        print()
        
    except Exception as e:
        print(f"Error saving output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
