import argparse
import json
import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scripts.tests.visualization_utils import print_document_hierarchy

def main():
    parser = argparse.ArgumentParser(description="Print the header hierarchy tree of a processed JSON file.")
    parser.add_argument("json_path", help="Path to the processed JSON file.")
    args = parser.parse_args()

    if not os.path.exists(args.json_path):
        print(f"Error: File not found at {args.json_path}")
        sys.exit(1)

    try:
        with open(args.json_path, "r") as f:
            data = json.load(f)
        
        print_document_hierarchy(data)
        
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {args.json_path}")
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    main()
