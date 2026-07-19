import { ChatSession, Message, DocumentFile, SearchMatch, Statistics } from "@/types"
import { apiClient } from "./apiClient"

interface AnswerResponse {
  success: boolean;
  question: string;
  answer: string;
  retrieval_confidence: string;
  sources: {
    document_name: string;
    page_number: number;
    chunk_id: number;
    similarity_score: number;
  }[];
  response_time: number;
  session_id: string;
}

interface StorageResponse {
  success: boolean;
  filename: string;
  document_id: string;
  collection_name: string;
  stored_chunks: number;
  vector_dimension: number;
  storage_time: number;
}

export const chatApi = {
  getSessions: async (): Promise<ChatSession[]> => {
    const response = await apiClient.get<ChatSession[]>("/api/chat/sessions")
    return response.data
  },
  
  createSession: async (title?: string, documentFilter?: string | null): Promise<ChatSession> => {
    const response = await apiClient.post<ChatSession>("/api/chat/session", {
      title: title || null,
      document_filter: documentFilter === "all" ? null : (documentFilter || null),
    })
    return response.data
  },

  deleteSession: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/chat/session/${id}`)
  },

  getMessages: async (sessionId: string): Promise<Message[]> => {
    const response = await apiClient.get<{ success: boolean; history: Message[] }>(`/api/chat/session/${sessionId}`)
    return response.data.history
  },

  sendMessage: async (sessionId: string, text: string, documentFilter?: string | null): Promise<Message> => {
    const response = await apiClient.post<AnswerResponse>("/api/chat", {
      question: text,
      session_id: sessionId,
      document_id: documentFilter === "all" ? null : (documentFilter || null),
    })
    const data = response.data
    return {
      message_id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      session_id: data.session_id || sessionId,
      role: "assistant",
      content: data.answer,
      timestamp: new Date().toISOString(),
      citations: data.sources || [],
      response_time: data.response_time,
    }
  },

  updateSession: async (id: string, updates: Partial<ChatSession>): Promise<ChatSession> => {
    const response = await apiClient.patch<ChatSession>(`/api/chat/session/${id}`, {
      title: updates.title,
      favorite: updates.favorite,
      pinned: updates.pinned,
      archived: updates.archived,
    })
    return response.data
  }
}

export const documentApi = {
  getDocuments: async (): Promise<DocumentFile[]> => {
    const response = await apiClient.get<{ documents: DocumentFile[] }>("/api/documents")
    return response.data.documents
  },

  uploadDocument: async (file: File): Promise<StorageResponse> => {
    const formData = new FormData()
    formData.append("file", file)
    const response = await apiClient.post<StorageResponse>("/api/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
    return response.data
  },

  deleteDocument: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/documents/${id}`)
  }
}

export const searchApi = {
  search: async (query: string, sessionId?: string | null): Promise<SearchMatch[]> => {
    const response = await apiClient.get<{ success: boolean; query: string; matches: SearchMatch[] }>("/api/chat/search", {
      params: {
        query,
        session_id: sessionId || undefined,
      },
    })
    return response.data.matches || []
  }
}

export const statisticsApi = {
  getStatistics: async (): Promise<Statistics> => {
    const response = await apiClient.get<Statistics>("/api/statistics")
    return response.data
  }
}
