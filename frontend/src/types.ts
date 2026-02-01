export interface Message {
    role: "user" | "assistant";
    content: string;
}

export interface ChunkMetadata {
    page_number: number;
    document_id: string;
    header_path_str: string;
    chunk_index?: number;
    is_table?: boolean;
}

export interface SourceChunk {
    chunk_id: string;
    text: string;
    metadata: ChunkMetadata;
    distance?: number;
}

export interface Citation {
    id: string;
    text: string;
    page: number;
    docId: string;
    headerPath?: string;
}
