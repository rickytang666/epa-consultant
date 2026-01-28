"""Simple script to ingest a JSON file with markdown content."""
import json
import sys
sys.path.insert(0, ".")

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
    # Load JSON
    with open("data/raw/test.json", "r") as f:
        data = json.load(f)
    
    # Parse markdown into chunks (with fix_headers=True)
    markdown = data["markdown"]
    ingestor = DocumentIngestor(fix_headers=True)
    doc = ingestor.ingest(markdown, filename="test.pdf")
    
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
    
    # Show first 10 chunks
    for chunk in doc.chunks[:10]:
        print(f"--- Chunk {chunk.chunk_index} (Page {chunk.location.page_number}) ---")
        
        # Print headers with hierarchical indentation
        if chunk.header_path:
            print("Headers:")
            # Sort headers by level number for proper hierarchy display
            sorted_headers = sorted(chunk.header_path, key=lambda h: int(h.level.split()[1]))
            for header in sorted_headers:
                level_num = int(header.level.split()[1])
                indent = "  " * level_num
                print(f"{indent}{header.level}: {header.name}")
            print()
        
        print(chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content)
        print()
        if len(chunk.content) > 200:
            print("..." + chunk.content[-200:])
        print()


if __name__ == "__main__":
    main()
