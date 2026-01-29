import os
import sys
import asyncio
import argparse
from glob import glob
from dotenv import load_dotenv

# Ensure backend modules are found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from data_processing.pdf_extractor import extract_pdf_async

# Load env vars
load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description="Run PDF extraction for files in data/raw.")
    parser.add_argument("filename", nargs="?", help="Specific PDF filename to process (optional).")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR processing.")
    args = parser.parse_args()

    raw_dir = os.path.abspath("data/raw")
    extracted_dir = os.path.abspath("data/extracted")
    
    # Ensure raw directory exists
    if not os.path.exists(raw_dir):
        print(f"Error: {raw_dir} does not exist.")
        sys.exit(1)

    # Determine files to process
    if args.filename:
        files = [os.path.join(raw_dir, args.filename)]
    else:
        files = glob(os.path.join(raw_dir, "*.pdf"))

    if not files:
        print("No PDF files found to process.")
        return

    print(f"Found {len(files)} file(s) to extract.")
    
    for pdf_path in files:
        if not os.path.exists(pdf_path):
            print(f"File not found: {pdf_path}")
            continue
            
        print(f"\nProcessing: {os.path.basename(pdf_path)}")
        try:
            result = await extract_pdf_async(
                pdf_path, 
                output_dir=extracted_dir,
                force_ocr=args.force_ocr
            )
            
            status = result.get("status")
            if status == "complete":
                print(f"SUCCESS: Extracted to {extracted_dir}")
            else:
                print(f"WARNING: Finished with status '{status}'")
                
        except Exception as e:
            print(f"ERROR: Failed to extract {os.path.basename(pdf_path)} - {e}")

if __name__ == "__main__":
    asyncio.run(main())
