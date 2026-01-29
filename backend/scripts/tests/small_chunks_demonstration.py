"""Simple script to ingest a JSON file with markdown content."""
import json
import sys
import os
import json
import sys
import os
import argparse

# Add backend directory to path

from data_processing.ingest import DocumentIngestor


def build_header_tree(chunks):
    """Build a nested tree structure from all chunk headers."""
    tree = {}
    
    for chunk in chunks:
        if not chunk.header_path:
            continue
        
        # Sort headers by level
        sorted_headers = sorted(chunk.header_path, key=lambda h: int(h.level.split()[1]))
        
        # Insert into tree
        current = tree
        for header in sorted_headers:
            key = (header.level, header.name)
            if key not in current:
                current[key] = {}
            current = current[key]
    
    return tree


def print_header_tree(tree, indent=0):
    """Recursively print the header tree."""
    for (level, name), children in tree.items():
        level_num = int(level.split()[1])
        prefix = "  " * level_num
        print(f"{prefix}{level}: {name}")
        print_header_tree(children, indent + 1)


def main():
    parser = argparse.ArgumentParser(description="Demonstrate chunking and table extraction.")
    parser.add_argument("file_path", help="Path to the PDF or JSON file to process.")
    parser.add_argument("--fix-headers", action="store_true", help="Enable header correction.")
    args = parser.parse_args()

    # Load data (auto-extracts if PDF)
    try:
        with open(args.file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    markdown = data["markdown"]
    filename = os.path.basename(args.file_path)
    
    print(f"Loaded markdown data from {filename}.")
    print(f"Header Correction: {'Enabled' if args.fix_headers else 'Disabled'}")

    # Run the pipeline
    ingestor = DocumentIngestor(fix_headers=args.fix_headers)
    doc = ingestor.ingest(
        markdown_text=markdown, 
        filename=filename
    )
    # Print results
    print(f"Document: {doc.filename}")
    print(f"Pages: {doc.total_pages}")
    print(f"Chunks: {len(doc.chunks)}")
    print()
    
    # Print header hierarchy tree
    print("=" * 60)
    print("HEADER HIERARCHY TREE")
    print("=" * 60)
    header_tree = build_header_tree(doc.chunks)
    print_header_tree(header_tree)
    print("=" * 60)
    print()


    # Scan all chunks for tables
    # print("\n--- Searching for Table Chunks ---")
    # table_count = 0
    # for chunk in doc.chunks:
    #     if chunk.metadata.get("type") == "table":
    #         table_count += 1
    #         print(f"--- Table Chunk {chunk.chunk_index} (Page {chunk.location.page_number}) ---")
    #         print(chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content)
    #         print("-" * 30)
    
    # print(f"Total Table Chunks Found: {table_count}\n")

    # Show sample text chunks
    for chunk in doc.chunks:
        
        # Print headers with hierarchical indentation
        if chunk.header_path:
            print('------------------------------------------------------------')
            print('Page:', chunk.location.page_number)
            print("Chunk Index:", chunk.chunk_index)
            print("Headers:")
            # Sort headers by level number for proper hierarchy display
            sorted_headers = sorted(chunk.header_path, key=lambda h: int(h.level.split()[1]))
            for header in sorted_headers:
                level_num = int(header.level.split()[1])
                indent = "  " * level_num
                print(f"{indent}{header.level}: {header.name}")
            print()
        
        if len(chunk.content) > 300:
            print(chunk.content[:250] + "...")
            print("..." + chunk.content[-250:])
        else:
            print(chunk.content)
        print()

    print("-" * 60)
    print(f"Total Cost: ${ingestor.total_cost:.6f}")
    print("-" * 60)


if __name__ == "__main__":
    main()
