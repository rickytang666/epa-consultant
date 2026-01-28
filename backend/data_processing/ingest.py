import os
import re
import uuid
from typing import List, Optional, Dict

from langchain_text_splitters import MarkdownHeaderTextSplitter
from .models import IngestedDocument, ProcessedChunk, ChunkLocation, SectionHeader

def simple_markdown_splitter(text: str) -> List[Dict]:
    """
    Splits markdown by headers (H1-H6).
    Returns list of dicts with 'content' and 'metadata' (headers).
    """
    lines = text.split('\n')
    chunks = []
    current_content = []
    current_headers = {}
    
    header_regex = re.compile(r'^(#{1,6})\s+(.*)')
    
    for line in lines:
        match = header_regex.match(line)
        if match:
            # If we have accumulated content, save it as a chunk
            if current_content:
                chunks.append({
                    "content": "\n".join(current_content).strip(),
                    "metadata": current_headers.copy()
                })
                current_content = []
            
            # Update headers
            level = len(match.group(1))
            name = match.group(2).strip()
            header_key = f"Header {level}"
            
            # Reset lower level headers (e.g. if we see H2, clear H3, H4...)
            keys_to_remove = [k for k in current_headers if int(k.split()[1]) >= level]
            for k in keys_to_remove:
                del current_headers[k]
                
            current_headers[header_key] = name
        else:
            current_content.append(line)
            
    # Add last chunk
    if current_content:
        chunks.append({
            "content": "\n".join(current_content).strip(),
            "metadata": current_headers.copy()
        })
        
    return chunks

def parse_markdown_to_chunks(
    markdown_text: str, 
    images: Dict[str, str],
    filename: str,
    doc_id: Optional[str] = None
) -> IngestedDocument:
    
    if doc_id is None:
        doc_id = str(uuid.uuid4())

    # 1. Extract Image Descriptions
    image_captions = {}
    pattern1 = r'!\[(.*?)\]\(\)!\[\]\((.*?)\)'
    for alt_text, img_path in re.findall(pattern1, markdown_text):
        if alt_text.strip(): image_captions[os.path.basename(img_path)] = alt_text.strip()
            
    pattern2 = r'!\[(.*?)\]\((.+?)\)'
    for alt_text, img_path in re.findall(pattern2, markdown_text):
        if img_path == ")![](": continue
        img_name = os.path.basename(img_path)
        if alt_text.strip() and img_name not in image_captions:
             image_captions[img_name] = alt_text.strip()

    # 2. Split by Page
    page_split_pattern = r'\n\n\{\d+\}------------------------------------------------\n\n'
    split_content = re.split(page_split_pattern, markdown_text)[1:]

    processed_chunks: List[ProcessedChunk] = []
    global_chunk_index = 0
    
    # Process Text
    for i in range(len(split_content)):
        curr_page = i + 1 
        page_text = split_content[i]
        
        # Use custom splitter
        sections = simple_markdown_splitter(page_text)
        
        for section in sections:
            content = section['content']
            if not content: continue
            
            global_chunk_index += 1
            header_breadcrumbs = []
            for h_tag, h_name in section['metadata'].items():
                header_breadcrumbs.append(SectionHeader(level=h_tag, name=h_name))

            processed_chunk = ProcessedChunk(
                document_id=doc_id,
                content=content,
                chunk_index=global_chunk_index,
                location=ChunkLocation(page_number=curr_page),
                header_path=header_breadcrumbs,
                metadata=section['metadata']
            )
            processed_chunks.append(processed_chunk)

    # Process Images
    for img_name, img_base64 in images.items():
        global_chunk_index += 1
        page_match = re.search(r'_page_(\d+)_', img_name)
        page_num = int(page_match.group(1)) + 1 if page_match else 1
        
        print(f"Uploading {img_name}...")
        image_url = upload_image_to_supabase(img_name, img_base64)
        
        caption = image_captions.get(img_name, "")
        if not caption:
            print(f"Generating caption for {img_name}...")
            caption = get_image_caption(img_base64)
        
        processed_chunk = ProcessedChunk(
            document_id=doc_id,
            content=f"Image Description for {img_name}: {caption}",
            chunk_index=global_chunk_index,
            location=ChunkLocation(page_number=page_num),
            metadata={
                "source": "image", 
                "filename": img_name, 
                "image_url": image_url,
                "has_image": True
            }
        )
        processed_chunks.append(processed_chunk)

    return IngestedDocument(
        id=doc_id,
        filename=filename,
        total_pages=len(split_content),
        chunks=processed_chunks
    )