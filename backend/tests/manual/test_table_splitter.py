import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from data_processing.table_splitter import split_markdown_table

def test_splitter():
    # Mock a large table
    header = "| Col 1 | Col 2 | Col 3 |\n|---|---|---|\n"
    rows = []
    for i in range(100):
        rows.append(f"| Row {i} Data 1 | Row {i} Data 2 | Row {i} Data 3 |")
    
    full_table = header + "\n".join(rows)
    print(f"Full table length: {len(full_table)}")
    
    # Split with small limit to force splitting
    splits = split_markdown_table(full_table, max_chars=500)
    
    print(f"Split into {len(splits)} chunks.")
    
    for i, s in enumerate(splits):
        print(f"\n--- Chunk {i} (len={len(s)}) ---")
        lines = s.strip().split('\n')
        print(f"Header preserved? {lines[0] == '| Col 1 | Col 2 | Col 3 |'}")
        print(f"Num lines: {len(lines)}")
        print(f"First data row: {lines[2]}")
        print(f"Last data row: {lines[-1]}")

if __name__ == "__main__":
    test_splitter()
