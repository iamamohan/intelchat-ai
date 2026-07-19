export interface Citation {
  document_name: string;
  page_number: number;
  chunk_id: number;
  similarity_score: number;
  snippet_text?: string;
}

export interface Message {
  message_id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  response_time?: number;
  citations?: Citation[];
}

export type DocumentStatus = 
  | "Uploading" 
  | "Extracting" 
  | "Chunking" 
  | "Embedding" 
  | "Indexing" 
  | "Ready" 
  | "Failed" 
  | "Deleted";

export interface DocumentFile {
  document_id: string;
  original_filename: string;
  stored_filename: string;
  upload_timestamp: string;
  sha256_hash: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  vector_count: number;
  embedding_model: string;
  status: DocumentStatus;
  progress?: number; // UI state only
}

export interface ChatSession {
  session_id: string;
  title: string;
  created_time: string;
  updated_time: string;
  message_count: number;
  document_filter: string | null;
  summary: string | null;
  status: string;
  last_accessed: string;
  total_tokens: number;
  favorite: boolean;
  archived: boolean;
  pinned: boolean;
}

// Design System types
export type ComponentVariant = "primary" | "secondary" | "outline" | "ghost" | "danger" | "success";
export type ComponentSize = "sm" | "md" | "lg";

export interface AppSettings {
  theme: "light" | "dark" | "system";
  isDevMode: boolean;
  fontSize: "sm" | "base" | "lg";
  autoScroll: boolean;
}

export interface SearchMatch {
  message_id: string;
  session_id: string;
  session_title: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  matchedText?: string;
}

export interface Statistics {
  total_documents: number;
  total_pages: number;
  total_chunks: number;
  total_embeddings: number;
  largest_document: { filename: string; file_size_bytes: number } | null;
  smallest_document: { filename: string; file_size_bytes: number } | null;
  average_pages: number;
  average_chunks: number;
  average_embedding_time_seconds: number;
  average_retrieval_time_seconds: number;
  average_chat_time_seconds: number;
  storage_used_mb: number;
  documents_by_status: Record<string, number>;
  chat_analytics: {
    total_sessions: number;
    total_messages: number;
  };
  llm_provider?: string;
}
