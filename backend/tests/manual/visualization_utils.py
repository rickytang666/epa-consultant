from typing import List, Dict, Any, Union

def build_header_tree(chunks: List[Any]) -> Dict:
    """
    Builds a nested tree structure from chunk headers.
    Supports both ProcessedChunk objects and dictionary representations.
    """
    tree = {}
    
    for chunk in chunks:
        # Handle dict vs object
        if isinstance(chunk, dict):
            headers = chunk.get("header_path", [])
        else:
            headers = getattr(chunk, "header_path", [])
            
        if not headers:
            continue
        
        # Helper to get level/name
        def get_level_name(h):
            if isinstance(h, dict):
                return h['level'], h['name']
            return h.level, h.name

        # Sort headers by level (H1 < H2 < H3)
        # Note: We assume standard "Header N" format
        try:
            sorted_headers = sorted(
                headers, 
                key=lambda h: int(get_level_name(h)[0].split()[1])
            )
        except (ValueError, IndexError):
            # Fallback for non-standard levels if any
            sorted_headers = headers

        # Insert into tree
        current = tree
        for header in sorted_headers:
            level, name = get_level_name(header)
            key = (level, name)
            if key not in current:
                current[key] = {}
            current = current[key]
            
    return tree

def print_header_tree(tree: Dict, indent: int = 0):
    """Recursively prints the header tree."""
    # Sort keys by level then name for consistent output
    def sort_key(k):
        level_str = k[0]
        try:
            num = int(level_str.split()[1])
        except:
            num = 0
        return (num, k[1])

    for key in sorted(tree.keys(), key=sort_key):
        level, name = key
        children = tree[key]
        
        # Calculate indent based on level number
        try:
            level_num = int(level.split()[1])
        except:
            level_num = indent
            
        prefix = "  " * level_num
        print(f"{prefix}{level}: {name}")
        print_header_tree(children, indent + 1)

def print_document_hierarchy(doc_data: Union[Dict, Any]):
    """
    Main entry point to print hierarchy from a document dict or object.
    """
    if isinstance(doc_data, dict):
        chunks = doc_data.get("chunks", [])
        filename = doc_data.get("filename", "Unknown File")
    else:
        chunks = getattr(doc_data, "chunks", [])
        filename = getattr(doc_data, "filename", "Unknown File")
        
    print("=" * 60)
    print(f"HIERARCHY FOR: {filename}")
    print("=" * 60)
    
    tree = build_header_tree(chunks)
    print_header_tree(tree)
    
    print("=" * 60)
