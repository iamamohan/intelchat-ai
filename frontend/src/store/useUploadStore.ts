"use client"

import { create } from "zustand"
import { DocumentFile, DocumentStatus } from "@/types"
import { documentApi } from "@/services/api"
import { toast } from "sonner"

interface UploadItem {
  id: string;
  name: string;
  size: number;
  progress: number;
  status: DocumentStatus;
  error?: string;
  file?: File;
}

interface UploadState {
  queue: UploadItem[];
  documents: DocumentFile[];
  isLoading: boolean;
  selectedDocumentId: string | null;
  
  // Actions
  loadDocuments: () => Promise<void>;
  addFileToQueue: (file: File) => Promise<void>;
  updateUploadItem: (id: string, updates: Partial<UploadItem>) => void;
  removeUploadItem: (id: string) => void;
  cancelUpload: (id: string) => void;
  retryUpload: (id: string) => void;
  
  // Document Operations
  addDocument: (doc: DocumentFile) => void;
  deleteDocument: (id: string) => Promise<void>;
  setDocuments: (docs: DocumentFile[]) => void;
  setSelectedDocumentId: (id: string | null) => void;
}

export const useUploadStore = create<UploadState>((set, get) => ({
  queue: [],
  documents: [],
  isLoading: false,
  selectedDocumentId: null,

  loadDocuments: async () => {
    set({ isLoading: true })
    try {
      const documents = await documentApi.getDocuments()
      set({ documents, isLoading: false })
    } catch (error) {
      set({ isLoading: false })
      console.error("Failed to load documents:", error)
      toast.error("Failed to load document library from backend")
    }
  },

  addFileToQueue: async (file) => {
    const uploadId = "upload-" + Math.random().toString(36).substring(2, 9)
    const newUpload: UploadItem = {
      id: uploadId,
      name: file.name,
      size: file.size,
      progress: 0,
      status: "Uploading",
      file,
    }

    set((state) => ({ queue: [newUpload, ...state.queue] }))

    // Simulate progress increments up to 95% while the single synchronous
    // API request is processing the document on the FastAPI backend
    let currentProgress = 0
    let isFinished = false
    let isFailed = false

    const interval = setInterval(() => {
      if (isFinished || isFailed) {
        clearInterval(interval)
        return
      }

      currentProgress += 5
      if (currentProgress > 95) {
        currentProgress = 95 // Hold at 95 until backend finishes processing
      }

      let status: DocumentStatus = "Uploading"
      if (currentProgress > 85) status = "Indexing"
      else if (currentProgress > 70) status = "Embedding"
      else if (currentProgress > 50) status = "Chunking"
      else if (currentProgress > 25) status = "Extracting"

      get().updateUploadItem(uploadId, { progress: currentProgress, status })
    }, 250)

    try {
      await documentApi.uploadDocument(file)
      isFinished = true
      clearInterval(interval)

      get().updateUploadItem(uploadId, { progress: 100, status: "Ready" })
      toast.success(`"${file.name}" uploaded and indexed successfully`)
      
      // Reload document list
      const docs = await documentApi.getDocuments()
      set({ documents: docs })

      // Auto-remove queue item after 3 seconds
      setTimeout(() => {
        get().removeUploadItem(uploadId)
      }, 3000)

    } catch (error) {
      isFailed = true
      clearInterval(interval)

      let errMsg = "Upload failed"
      const err = error as { response?: { data?: { message?: string } }; message?: string }
      if (err.response?.data?.message) {
        errMsg = err.response.data.message
      } else if (err.message) {
        errMsg = err.message
      }

      get().updateUploadItem(uploadId, {
        status: "Failed",
        progress: 100,
        error: errMsg
      })
      toast.error(`Failed to process "${file.name}": ${errMsg}`)
    }
  },

  updateUploadItem: (id, updates) => set((state) => ({
    queue: state.queue.map((item) => (item.id === id ? { ...item, ...updates } : item)),
  })),

  removeUploadItem: (id) => set((state) => ({
    queue: state.queue.filter((item) => item.id !== id),
  })),

  cancelUpload: (id) => set((state) => ({
    queue: state.queue.filter((item) => item.id !== id),
  })),

  retryUpload: async (id) => {
    const item = get().queue.find((q) => q.id === id)
    if (item && item.file) {
      get().removeUploadItem(id)
      await get().addFileToQueue(item.file)
    }
  },

  addDocument: (doc) => set((state) => ({
    documents: [doc, ...state.documents],
  })),

  deleteDocument: async (id) => {
    try {
      await documentApi.deleteDocument(id)
      set((state) => ({
        documents: state.documents.filter((d) => d.document_id !== id),
      }))
    } catch (error) {
      console.error(`Failed to delete document ${id}:`, error)
      toast.error("Failed to delete document from backend")
    }
  },

  setDocuments: (docs) => set({ documents: docs }),
  
  setSelectedDocumentId: (id) => set({ selectedDocumentId: id }),
}))
