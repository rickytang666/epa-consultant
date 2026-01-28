"""Script to test skeleton summary generation."""
import json
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_processing.ingest import DocumentIngestor

def main():
    # Load JSON
    with open("data/raw/test.json", "r") as f:
        data = json.load(f)
    
    markdown = data["markdown"]
    print("Loaded markdown data.")
    
    # Run the pipeline
    print("Running ingestion pipeline...")
    ingestor = DocumentIngestor(fix_headers=True)
    doc = ingestor.ingest(
        markdown_text=markdown, 
        filename="test.pdf"
    )
    
    print(f"Total pages: {doc.total_pages}")
    print(f"Merged Section Chunks (for summaries): {len(doc.section_chunks)}")
    print(f"Final RAG Chunks: {len(doc.chunks)}")
    
    # Generate Skeleton Summaries using the section_chunks
    print("=" * 60)
    print("GENERATING SKELETON SUMMARIES")
    print("=" * 60)
    
    summaries = ingestor.generate_skeleton_summaries_sync(doc.section_chunks)
    
    print()
    print("=" * 60)
    print("SKELETON SUMMARIES REPORT")
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

if __name__ == "__main__":
    main()
