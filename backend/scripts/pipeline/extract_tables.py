
import json
import re
import uuid
from pathlib import Path

def extract_tables_from_markdown():
    # 1. Paths
    base_dir = Path(__file__).parent.parent.parent # backend/
    data_dir = base_dir / "data"
    input_path = data_dir / "extracted" / "document.json"
    output_path = data_dir / "processed" / "tables.json"
    
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        return

    # 2. Load Markdown
    with open(input_path, "r") as f:
        doc_data = json.load(f)
        markdown_text = doc_data.get("markdown", "")
        doc_id = str(uuid.uuid4()) # We don't have the original doc ID handy inside document.json usually, or we can reuse one if we had it.

    print(f"Loaded markdown ({len(markdown_text)} chars). Parsing tables...")

    # 3. Parse Line by Line
    lines = markdown_text.split("\n")
    
    tables = []
    current_table_lines = []
    
    # Context trackers
    current_page = 1
    table_start_page = 1
    header_stack = [] # List of {"level": int, "name": str}
    last_non_empty_line = ""
    last_table_content = "" # For deduplication assumption
    
    # Regex
    # Page break: {123}---------------- or similar
    page_break_pattern = re.compile(r"^\{(\d+)\}-+$")
    # Headers: # Title, ## Subtitle
    header_pattern = re.compile(r"^(#+)\s*(.+)")

    def flush_table():
        nonlocal current_table_lines, last_table_content, table_start_page
        if not current_table_lines:
            return

        # Filtering
        # Markdown tables usually need at least header + separator + row (3 lines).
        # But let's keep even 2 lines just in case.
        if len(current_table_lines) < 2:
            current_table_lines = []
            return

        content = "\n".join(current_table_lines)
        
        # Deduplication (Simple)
        if content == last_table_content:
            # print(f"Skipping duplicate table on page {table_start_page}")
            current_table_lines = []
            return

        # Construct Header Path
        # Convert header_stack to the format frontend likely wants
        h_path = [{"level": f"H{h['level']}", "name": h['name']} for h in header_stack]
        if not h_path:
             h_path = [{"level": "Context", "name": "Document"}]

        # Metadata
        table_uuid = str(uuid.uuid4())
        
        # Title Heuristic: Use last non-empty line seen BEFORE the table started
        # If the last line looks like "Table X: ..." that's a winner.
        title = last_non_empty_line if len(last_non_empty_line) < 200 else f"Table on Page {table_start_page}"
        if not title:
            title = f"Table on Page {table_start_page}"
        
        # Cleanup title
        # Remove markdown bold/italic
        title = title.replace("*", "").strip()
        # Remove HTML tags (e.g. <sup>1</sup>)
        title = re.sub(r"<[^>]+>", "", title).strip()
        
        tables.append({
            "chunk_id": table_uuid,
            "document_id": doc_id,
            "content": content,
            "chunk_index": 0,
            "location": {"page_number": table_start_page}, 
            "header_path": h_path,
            "metadata": {
                "is_table": True,
                "table_id": table_uuid,
                "table_title": title
            }
        })
        
        last_table_content = content
        current_table_lines = []

    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check page break
        m_page = page_break_pattern.match(line)
        if m_page:
            try:
                current_page = int(m_page.group(1))
            except:
                pass
            continue

        # Page Limit Check (after 151 all templates)
        if current_page >= 151:
            if current_table_lines:
                flush_table()
            continue
            
        # Ignore empty lines (allow continuity across page breaks)
        if not line:
            continue

        # Ignore Horizontal Rules (---) often found at page breaks
        # We only ignore them if we are tracking a table. 
        # If we hit a Header next, that will still flush the table.
        if re.match(r"^[-*]{3,}$", line):
            continue

        # Check Header
        m_header = header_pattern.match(line)
        if m_header:
            # If we hit a header, any active table is definitely finished
            if current_table_lines:
                flush_table()
            
            level = len(m_header.group(1))
            text = m_header.group(2).strip()
            
            # Update stack: remove headers of same or deeper level
            while header_stack and header_stack[-1]['level'] >= level:
                header_stack.pop()
            
            header_stack.append({'level': level, 'name': text})
            last_non_empty_line = text 
            continue

        # Check Table Row
        if line.startswith("|"):
            if not current_table_lines:
                table_start_page = current_page
            current_table_lines.append(line)
        else:
            # Check for "Orphan Rows" (lost pipes) - frequent in this doc's Appendices
            # Pattern: Code (9-10 chars) + Space + Description
            # e.g. "WAG87####E Federal..."
            # We only do this if we are ALREADY in a table (continuation)
            if current_table_lines:
                # Regex: Start with 9-10 alphanumeric/hash chars, then space
                m_orphan = re.match(r"^([A-Z0-9#]{9,10})\s+(.*)$", line)
                if m_orphan:
                    # Reconstruct table row
                    code = m_orphan.group(1)
                    desc = m_orphan.group(2)
                    current_table_lines.append(f"| {code} | {desc} |")
                    # Do NOT update last_non_empty_line here; we want to preserve the Title candidate (header)
                    continue

            # Not a table line -> End of table
            if current_table_lines:
                flush_table()
            
            last_non_empty_line = line

    # Flush last table
    if current_table_lines:
        flush_table()

    print(f"Found {len(tables)} tables.")
    
    # 4. Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(tables, f, indent=2)
    
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    extract_tables_from_markdown()
