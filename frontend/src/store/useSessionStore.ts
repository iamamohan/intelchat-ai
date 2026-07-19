"use client"

import { create } from "zustand"
import { ChatSession, Message } from "@/types"
import { chatApi } from "@/services/api"
import { toast } from "sonner"

interface SessionState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messagesBySession: Record<string, Message[]>;
  isLoading: boolean;
  isLoadingMessages: boolean;
  
  // Actions
  setActiveSessionId: (id: string | null) => void;
  loadSessions: () => Promise<void>;
  loadMessages: (sessionId: string) => Promise<void>;
  createSession: (title?: string, documentFilter?: string | null) => Promise<string>;
  deleteSession: (id: string) => Promise<void>;
  updateSession: (id: string, updates: Partial<ChatSession>) => Promise<void>;
  sendMessage: (sessionId: string, text: string, documentFilter?: string | null) => Promise<void>;
  addMessage: (sessionId: string, message: Message) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messagesBySession: {},
  isLoading: false,
  isLoadingMessages: false,

  setActiveSessionId: (id) => set({ activeSessionId: id }),
  
  loadSessions: async () => {
    set({ isLoading: true })
    try {
      const sessions = await chatApi.getSessions()
      set({ sessions, isLoading: false })
      
      // Auto-select first session if none is selected
      const currentActive = get().activeSessionId
      if (sessions.length > 0 && (!currentActive || !sessions.some(s => s.session_id === currentActive))) {
        set({ activeSessionId: sessions[0].session_id })
      } else if (sessions.length === 0) {
        set({ activeSessionId: null })
      }
    } catch (error) {
      set({ isLoading: false })
      console.error("Failed to load sessions:", error)
      toast.error("Failed to load chat sessions from server")
    }
  },

  loadMessages: async (sessionId: string) => {
    set({ isLoadingMessages: true })
    try {
      const msgs = await chatApi.getMessages(sessionId)
      set((state) => ({
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: msgs
        },
        isLoadingMessages: false
      }))
    } catch (error) {
      set({ isLoadingMessages: false })
      console.error(`Failed to load messages for session ${sessionId}:`, error)
      toast.error("Failed to load message history")
    }
  },
  
  createSession: async (title, documentFilter) => {
    set({ isLoading: true })
    try {
      const newSession = await chatApi.createSession(title, documentFilter)
      set((state) => ({
        sessions: [newSession, ...state.sessions],
        activeSessionId: newSession.session_id,
        messagesBySession: {
          ...state.messagesBySession,
          [newSession.session_id]: []
        },
        isLoading: false
      }))
      toast.success("New chat session created")
      return newSession.session_id
    } catch (error) {
      set({ isLoading: false })
      console.error("Failed to create session:", error)
      toast.error("Failed to create new session")
      throw error
    }
  },

  deleteSession: async (id) => {
    try {
      await chatApi.deleteSession(id)
      set((state) => {
        const updated = state.sessions.filter((s) => s.session_id !== id)
        const currentActive = state.activeSessionId
        let nextActive = currentActive
        if (currentActive === id) {
          nextActive = updated.length > 0 ? updated[0].session_id : null
        }
        
        // Clean up messages cache
        const newMessagesBySession = { ...state.messagesBySession }
        delete newMessagesBySession[id]

        return {
          sessions: updated,
          activeSessionId: nextActive,
          messagesBySession: newMessagesBySession
        }
      })
      toast.success("Session deleted successfully")
    } catch (error) {
      console.error(`Failed to delete session ${id}:`, error)
      toast.error("Failed to delete chat session")
    }
  },

  updateSession: async (id, updates) => {
    try {
      const updated = await chatApi.updateSession(id, updates)
      set((state) => ({
        sessions: state.sessions.map((s) => s.session_id === id ? updated : s)
      }))
    } catch (error) {
      console.error(`Failed to update session ${id}:`, error)
      toast.error("Failed to update session settings")
    }
  },

  sendMessage: async (sessionId, text, documentFilter) => {
    const userMsg: Message = {
      message_id: `user-${Date.now()}`,
      session_id: sessionId,
      role: "user",
      content: text,
      timestamp: new Date().toISOString()
    }

    // Immediately add user message to list for optimistic display
    get().addMessage(sessionId, userMsg)
    set({ isLoadingMessages: true }) // Reuse loading messages for typing indicator

    try {
      const assistantMsg = await chatApi.sendMessage(sessionId, text, documentFilter)
      get().addMessage(sessionId, assistantMsg)
      
      // Refresh the session list in background to update last_accessed, message count, and title
      const sessions = await chatApi.getSessions()
      set({ sessions })
    } catch (error) {
      console.error("Failed to send message:", error)
      let errMsg = "Failed to get AI response"
      const err = error as { response?: { data?: { message?: string } } }
      if (err.response?.data?.message) {
        errMsg = err.response.data.message
      }
      toast.error(errMsg)

      // Add a system error message in the chat
      const errorMsg: Message = {
        message_id: `error-${Date.now()}`,
        session_id: sessionId,
        role: "assistant",
        content: `❌ **Error**: ${errMsg}. Please ensure the backend is running and your API key is valid.`,
        timestamp: new Date().toISOString()
      }
      get().addMessage(sessionId, errorMsg)
    } finally {
      set({ isLoadingMessages: false })
    }
  },

  addMessage: (sessionId, message) => set((state) => {
    const currentMsgs = state.messagesBySession[sessionId] || []
    return {
      messagesBySession: {
        ...state.messagesBySession,
        [sessionId]: [...currentMsgs, message]
      }
    }
  })
}))
