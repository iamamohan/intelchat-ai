"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { isToday, isYesterday } from "date-fns"
import {
  MessageSquare,
  Edit2,
  Trash2,
  Plus,
  FileText,
  UploadCloud,
  ChevronDown,
  ChevronRight,
  Pin
} from "lucide-react"
import { useUIStore } from "@/store/useUIStore"
import { useSessionStore } from "@/store/useSessionStore"
import { useUploadStore } from "@/store/useUploadStore"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export function Sidebar() {
  const router = useRouter()
  const { isSidebarOpen } = useUIStore()
  const { 
    sessions, 
    activeSessionId, 
    setActiveSessionId, 
    createSession, 
    loadSessions,
    deleteSession,
    updateSession
  } = useSessionStore()
  const { 
    documents, 
    loadDocuments, 
    queue, 
    addFileToQueue, 
    deleteDocument, 
    selectedDocumentId, 
    setSelectedDocumentId 
  } = useUploadStore()

  const [docsExpanded, setDocsExpanded] = React.useState(true)

  React.useEffect(() => {
    loadSessions()
    loadDocuments()
  }, [loadSessions, loadDocuments])

  const pinnedSessions = sessions.filter(s => s.pinned)
  const unpinnedSessions = sessions.filter(s => !s.pinned)

  const todaySessions = unpinnedSessions.filter(s => isToday(new Date(s.last_accessed || s.updated_time)))
  const yesterdaySessions = unpinnedSessions.filter(s => isYesterday(new Date(s.last_accessed || s.updated_time)))
  const olderSessions = unpinnedSessions.filter(s => !isToday(new Date(s.last_accessed || s.updated_time)) && !isYesterday(new Date(s.last_accessed || s.updated_time)))

  const handleNewChat = async () => {
    try {
      const newId = await createSession("New Chat")
      setActiveSessionId(newId)
      setSelectedDocumentId(null)
      router.push(`/?session=${newId}`)
      setTimeout(() => document.getElementById("chat-input")?.focus(), 100)
    } catch (err) {
      console.error(err)
    }
  }

  const handleRenameSession = async (e: React.MouseEvent, sessionId: string, currentTitle: string) => {
    e.preventDefault()
    e.stopPropagation()
    const newTitle = prompt("Enter new title for this chat:", currentTitle)
    if (newTitle && newTitle.trim()) {
      await updateSession(sessionId, { title: newTitle.trim() })
    }
  }

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.preventDefault()
    e.stopPropagation()
    if (confirm("Are you sure you want to delete this chat session?")) {
      await deleteSession(sessionId)
    }
  }

  const handleTogglePin = async (e: React.MouseEvent, sessionId: string, currentPinned: boolean) => {
    e.preventDefault()
    e.stopPropagation()
    await updateSession(sessionId, { pinned: !currentPinned })
  }

  const renderSessionGroup = (title: string, items: typeof sessions) => {
    if (items.length === 0) return null;
    return (
      <div className="space-y-1 mt-6 first:mt-2">
        <span className="text-[11px] font-semibold text-muted-foreground px-3 mb-2 block">
          {title}
        </span>
        {items.map((session) => {
          const date = new Date(session.last_accessed || session.updated_time)
          const timeString = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          return (
            <Link key={session.session_id} href={`/?session=${session.session_id}`}>
              <div
                className={cn(
                  "flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-[14px] transition-all cursor-pointer group",
                  activeSessionId === session.session_id
                    ? "bg-sidebar-accent text-foreground font-medium"
                    : "text-secondary-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                )}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate">{session.title}</span>
                </div>
                
                <div className="flex items-center shrink-0">
                  <span className="text-[10px] text-muted-foreground group-hover:hidden block mr-1">
                    {timeString}
                  </span>
                  <div className="hidden group-hover:flex items-center">
                    <button
                      onClick={(e) => handleTogglePin(e, session.session_id, !!session.pinned)}
                      className={cn("p-1 rounded hover:bg-sidebar hover:text-foreground", session.pinned ? "text-primary" : "text-muted-foreground")}
                    >
                      <Pin className="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => handleRenameSession(e, session.session_id, session.title)}
                      className="p-1 rounded hover:bg-sidebar text-muted-foreground hover:text-foreground"
                    >
                      <Edit2 className="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => handleDeleteSession(e, session.session_id)}
                      className="p-1 rounded hover:bg-sidebar text-muted-foreground hover:text-error"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    )
  }

  return (
    <aside className={cn(
      "flex flex-col h-full bg-sidebar border-r border-sidebar-border select-none shrink-0 relative overflow-hidden transition-all duration-300 z-40",
      isSidebarOpen ? "w-[260px]" : "w-0 md:w-0 border-r-0 opacity-0 overflow-hidden"
    )}>
      <div className="h-16 flex items-center justify-start px-4 shrink-0 mt-2">
        <div className="flex items-center gap-2.5">
          <div className="relative size-7 shrink-0 rounded overflow-hidden flex items-center justify-center">
            <Image src="/logo.png" alt="Logo" width={28} height={28} className="object-contain" />
          </div>
          <span className="font-semibold text-[15px] text-foreground tracking-tight">
            IntelChat
          </span>
        </div>
      </div>

      <div className="px-3 pb-2 shrink-0 mt-4">
        <Button
          onClick={handleNewChat}
          className="w-full justify-start bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm rounded-lg h-10 font-medium px-4 transition-colors"
        >
          <div className="flex items-center justify-center w-full gap-2">
            <Plus className="size-4" />
            <span className="text-[14px]">New Chat</span>
          </div>
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4 mt-2 custom-scrollbar">
        {renderSessionGroup("Pinned", pinnedSessions)}
        {renderSessionGroup("Today", todaySessions)}
        {renderSessionGroup("Yesterday", yesterdaySessions)}
        {renderSessionGroup("Older", olderSessions)}
        
        {/* Documents Section */}
        <div className="mt-8">
          <div 
            className="flex items-center justify-between px-3 mb-2 cursor-pointer group"
            onClick={() => setDocsExpanded(!docsExpanded)}
          >
            <span className="text-[11px] font-semibold text-muted-foreground group-hover:text-foreground transition-colors uppercase tracking-wider flex items-center gap-1">
              {docsExpanded ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
              Documents ({documents.length})
            </span>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <label 
                className="p-1 rounded hover:bg-sidebar-accent text-muted-foreground hover:text-foreground cursor-pointer"
                onClick={(e) => e.stopPropagation()}
              >
                <input 
                  type="file" 
                  className="hidden" 
                  accept=".pdf" 
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      addFileToQueue(file)
                      setDocsExpanded(true)
                    }
                    e.target.value = ''
                  }} 
                />
                <UploadCloud className="size-3.5" />
              </label>
            </div>
          </div>
          
          {docsExpanded && (
            <div className="space-y-0.5">
              <div
                onClick={() => setSelectedDocumentId(null)}
                className={cn(
                  "flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-[14px] transition-all cursor-pointer group",
                  selectedDocumentId === null
                    ? "bg-sidebar-accent text-foreground font-medium"
                    : "text-secondary-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                )}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate">All Documents</span>
                </div>
              </div>

              {/* Upload Queue */}
              {queue.map(item => (
                <div key={item.id} className="flex flex-col gap-1 px-3 py-2 rounded-lg bg-sidebar-accent/30 text-[14px] text-foreground mx-2 mb-1 border border-border/50">
                  <div className="flex items-center justify-between">
                    <span className="truncate max-w-[140px]">{item.name}</span>
                    <span className="text-[10px] text-muted-foreground">{item.progress}%</span>
                  </div>
                  <div className="w-full bg-border rounded-full h-1">
                    <div className="bg-primary h-1 rounded-full transition-all duration-300" style={{ width: `${item.progress}%` }} />
                  </div>
                  <span className="text-[10px] text-muted-foreground">{item.status}</span>
                </div>
              ))}

              {documents.length === 0 && queue.length === 0 ? (
                <div className="px-3 py-4 text-center border-2 border-dashed border-sidebar-border/60 rounded-lg mx-2 mt-2">
                  <span className="text-[11px] text-muted-foreground">No documents uploaded</span>
                </div>
              ) : (
                documents.map(doc => {
                  const date = new Date(doc.upload_timestamp)
                  const dateStr = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                  const isSelected = selectedDocumentId === doc.document_id
                  
                  return (
                    <div 
                      key={doc.document_id} 
                      onClick={() => setSelectedDocumentId(doc.document_id)}
                      className={cn(
                        "flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-[13px] transition-all cursor-pointer group",
                        isSelected
                          ? "bg-sidebar-accent text-foreground font-medium"
                          : "text-secondary-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                      )}
                    >
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <FileText className={cn("size-3.5 shrink-0", isSelected ? "text-primary" : "text-muted-foreground")} />
                        <span className="truncate" title={doc.original_filename}>{doc.original_filename}</span>
                      </div>
                      <div className="flex items-center shrink-0">
                        <span className="text-[10px] text-muted-foreground group-hover:hidden shrink-0">
                          {dateStr}
                        </span>
                        <div className="hidden group-hover:flex items-center">
                          <button
                            onClick={async (e) => {
                              e.stopPropagation()
                              if (confirm("Delete this document?")) {
                                await deleteDocument(doc.document_id)
                                if (isSelected) setSelectedDocumentId(null)
                              }
                            }}
                            className="p-1 rounded hover:bg-sidebar text-muted-foreground hover:text-error"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          )}
        </div>
      </div>

      <div className="p-4 mt-auto shrink-0 border-t border-sidebar-border/50 select-none">
        <div className="flex items-center gap-3">
          <div className="relative size-6 shrink-0 rounded overflow-hidden flex items-center justify-center">
            <Image src="/logo.png" alt="Logo" width={24} height={24} className="object-contain" />
          </div>
          <div className="flex flex-col">
            <span className="text-[13px] font-medium text-foreground tracking-tight leading-none">IntelChat</span>
            <span className="text-[11px] text-muted-foreground mt-1 leading-none">Version 1.0</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
