import os
import sys
import argparse
import json
from glob import glob
from dotenv import load_dotenv

# Ensure backend modules are found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from data_processing.ingest import DocumentIngestor

# Load env vars
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Run parsing/ingestion for files in data/extracted.")
    parser.add_argument("filename", nargs="?", help="Specific JSON filename to process (optional).")
    parser.add_argument("--fix-headers", action="store_true", help="Enable header correction LLM step.")
    parser.add_argument("--skip-summaries", action="store_true", help="Skip summary generation.")
    args = parser.parse_args()

    extracted_dir = os.path.abspath("data/extracted")
    processed_dir = os.path.abspath("data/processed")
    
    # Ensure directories exist
    if not os.path.exists(extracted_dir):
        print(f"Error: {extracted_dir} does not exist. Run PDF extraction first.")
        sys.exit(1)
        
    os.makedirs(processed_dir, exist_ok=True)

    # Determine files to process
    if args.filename:
        # If user passes "test.pdf", we look for "test.json"
        base_name = os.path.splitext(args.filename)[0]
        json_file = os.path.join(extracted_dir, base_name + ".json")
        files = [json_file]
    else:
        files = glob(os.path.join(extracted_dir, "*.json"))

    if not files:
        print("No extracted JSON files found to process.")
        return

    print(f"Found {len(files)} file(s) to parse.")
    
    ingestor = DocumentIngestor(fix_headers=args.fix_headers)

    for json_path in files:
        if not os.path.exists(json_path):
            print(f"File not found: {json_path}")
            continue
            
        print(f"\nParsing: {os.path.basename(json_path)}")
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            
            markdown = data.get("markdown", "")
            if not markdown:
                print("Skipping: No markdown content found.")
                continue
                
            # Use original filename if possible, else derive from JSON name
            original_filename = os.path.basename(json_path).replace(".json", ".pdf")
            
            doc = ingestor.ingest(markdown, filename=original_filename)
            
            # Generate summaries by default
            if not args.skip_summaries:
                print("Generating skeleton summaries...")
                summaries, sum_cost = ingestor.generate_skeleton_summaries_sync(doc.chunks)
                doc.section_summaries = summaries
                
                print("Generating document summary...")
                doc_summary, doc_cost = ingestor.generate_document_summary(summaries, original_filename)
                doc.document_summary = doc_summary
                
                doc.costs["skeleton_summaries"] = sum_cost
                doc.costs["document_summary"] = doc_cost
                doc.costs["total"] = doc.costs.get("header_correction", 0.0) + sum_cost + doc_cost
            
            # Save output as separate files
            
            # Save chunks.json
            chunks_path = os.path.join(processed_dir, "chunks.json")
            chunks_data = [chunk.model_dump() for chunk in doc.chunks]
            
            # Save tables.json
            tables_path = os.path.join(processed_dir, "tables.json")
            tables_data = [
                chunk.model_dump() 
                for chunk in doc.chunks 
                if chunk.metadata.is_table
            ]
            
            with open(chunks_path, "w") as f:
                json.dump(chunks_data, f, indent=2, default=str)
            
            with open(tables_path, "w") as f:
                json.dump(tables_data, f, indent=2, default=str)
                
            print(f"SUCCESS: Processed {os.path.basename(json_path)}")
            print(f"  - Chunks: {chunks_path}")
            print(f"  - Tables: {tables_path}")
            print(f"  - Document ID: {doc.document_id}")
            print(f"  - Total Chunks: {len(doc.chunks)}")
            print(f"  - Table Chunks: {len(tables_data)}")
                
        except Exception as e:
            print(f"ERROR: Failed to parse {os.path.basename(json_path)} - {e}")

if __name__ == "__main__":
    main()
