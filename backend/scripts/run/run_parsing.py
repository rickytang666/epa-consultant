import os
import sys
import argparse
import json
from glob import glob
from dotenv import load_dotenv

# Ensure backend modules are found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from data_processing.ingest import DocumentIngestor
from data_processing.llm_client import LLMClient

# Load env vars
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Run parsing/ingestion for files in data/extracted.")
    parser.add_argument("filename", nargs="?", help="Specific JSON filename to process (optional).")
    parser.add_argument("--fix-headers", action="store_true", help="Enable header correction LLM step.")
    parser.add_argument("--skip-summaries", action="store_true", help="Skip summary generation.")
    args = parser.parse_args()
    
    # 0. API Key Check
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    
    # Red color codes for terminal
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    # Determine if we need keys
    needs_llm = not args.skip_summaries or args.fix_headers
    
    if needs_llm:
        print("Checking API availability and quota...")
        llm = LLMClient()
        provider = llm.select_best_provider()
        
        if not provider:
            print(f"\n{BOLD}{RED}WARNING: All API keys are invalid or quota exhausted!{RESET}")
            print(f"{RED}Summaries and header correction cannot proceed.{RESET}")
            print(f"{RED}REVERTING TO SKIP-SUMMARIES MODE.{RESET}\n")
            args.skip_summaries = True
            args.fix_headers = False
        else:
            print(f"✓ Using {BOLD}{provider.upper()}{RESET} for all operations.\n")

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
                try:
                    print("Generating skeleton summaries...")
                    summaries, sum_cost = ingestor.generate_skeleton_summaries_sync(doc.chunks)
                    # Stringify tuple keys for JSON serialization
                    doc.section_summaries = {
                        " > ".join([h[1] for h in k]) if k else "Root": v 
                        for k, v in summaries.items()
                    }
                    
                    print("Generating document summary...")
                    doc_summary, doc_cost = ingestor.generate_document_summary(summaries, original_filename)
                    doc.document_summary = doc_summary
                    
                    doc.costs["skeleton_summaries"] = sum_cost
                    doc.costs["document_summary"] = doc_cost
                    doc.costs["total"] = doc.costs.get("header_correction", 0.0) + sum_cost + doc_cost
                    
                except Exception as e:
                    print(f"{BOLD}{RED}WARNING: Summary generation failed (likely quota/network). Skipping summaries.{RESET}")
                    print(f"{RED}Error details: {e}{RESET}")
                    # Continue without summaries
                    doc.section_summaries = {}
                    doc.document_summary = ""
            
            # Save output as separate files
            
            # Save Chunks & Summaries (Full ProcessedDocument)
            chunks_path = os.path.join(processed_dir, "chunks.json")
            
            # Save tables.json (extract table chunks for separate view)
            tables_path = os.path.join(processed_dir, "tables.json")
            tables_data = [
                chunk.model_dump() 
                for chunk in doc.chunks 
                if chunk.metadata.is_table
            ]
            
            # Write full document to chunks.json
            with open(chunks_path, "w") as f:
                json.dump(doc.model_dump(), f, indent=2, default=str)
            
            # Write tables only to tables.json (as a list of chunks)
            with open(tables_path, "w") as f:
                json.dump(tables_data, f, indent=2, default=str)
                
            print(f"SUCCESS: Processed {os.path.basename(json_path)}")
            print(f"  - Chunks: {chunks_path}")
            print(f"  - Tables: {tables_path}")
            print(f"  - Document ID: {doc.document_id}")
            print(f"  - Total Chunks: {len(doc.chunks)}")
            print(f"  - Table Chunks: {len(tables_data)}")
                
        except Exception as e:
            print(f"{RED}ERROR: Failed to parse {os.path.basename(json_path)} - {e}{RESET}")

if __name__ == "__main__":
    main()
