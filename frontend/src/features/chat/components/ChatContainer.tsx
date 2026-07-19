"use client"

import * as React from "react"
import { Send, Bot, Square } from "lucide-react"
import { useSessionStore } from "@/store/useSessionStore"
import { useUploadStore } from "@/store/useUploadStore"
import { MessageItem } from "./MessageItem"
import { WelcomeScreen } from "@/features/welcome/components/WelcomeScreen"
import { Button } from "@/components/ui/button"

export function ChatContainer() {
  const { 
    activeSessionId, 
    messagesBySession, 
    isLoadingMessages,
    loadMessages,
    sendMessage
  } = useSessionStore()

  const { loadDocuments, selectedDocumentId, addFileToQueue } = useUploadStore()
  
  const [input, setInput] = React.useState("")
  const [prevSessionId, setPrevSessionId] = React.useState<string | null>(null)
  const [isDragging, setIsDragging] = React.useState(false)
  const [loadingStep, setLoadingStep] = React.useState(0)
  
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)
  const chatEndRef = React.useRef<HTMLDivElement>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const messages = React.useMemo(() => {
    return activeSessionId ? messagesBySession[activeSessionId] || [] : []
  }, [activeSessionId, messagesBySession])

  // Adjust state during render when active session changes
  if (activeSessionId !== prevSessionId) {
    setPrevSessionId(activeSessionId)
  }

  React.useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  React.useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId)
    }
  }, [activeSessionId, loadMessages])

  const scrollToBottom = React.useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  React.useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom()
    }
  }, [messages.length, scrollToBottom])

  React.useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = "auto"
    const scrollHeight = textarea.scrollHeight
    textarea.style.height = `${Math.min(scrollHeight, 144)}px` // max 6 rows approx
  }, [input])

  React.useEffect(() => {
    let interval: NodeJS.Timeout
    if (isLoadingMessages) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoadingStep(0)
      interval = setInterval(() => {
        setLoadingStep(prev => (prev < 2 ? prev + 1 : prev))
      }, 800)
    }
    return () => clearInterval(interval)
  }, [isLoadingMessages])

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = e.dataTransfer.files
    if (files.length > 0 && files[0].type === "application/pdf") {
      addFileToQueue(files[0])
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type === "application/pdf") {
      addFileToQueue(file)
    }
    if (e.target) {
      e.target.value = ''
    }
  }

  const handleSend = async () => {
    if (!input.trim() || !activeSessionId) return
    const text = input.trim()
    setInput("")
    
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }

    await sendMessage(activeSessionId, text, selectedDocumentId)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!activeSessionId) {
    return <WelcomeScreen />
  }

  return (
    <div className="flex-1 flex min-w-0 bg-background relative overflow-hidden" onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
      {isDragging && (
        <div className="absolute inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center border-4 border-dashed border-primary m-4 rounded-xl">
          <div className="flex flex-col items-center gap-4 p-8 bg-surface rounded-2xl shadow-lg animate-in fade-in zoom-in-95">
            <div className="size-16 rounded-full bg-primary/20 flex items-center justify-center text-primary">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
            </div>
            <h3 className="text-[20px] font-semibold text-foreground tracking-tight">Drop PDF here</h3>
            <p className="text-[14px] text-muted-foreground">Upload and instantly select this document</p>
          </div>
        </div>
      )}
      
      <div className="flex-1 flex flex-col min-w-0 relative">
        <div className="flex-1 overflow-y-auto min-h-0 custom-scrollbar pb-40">
          <div className="max-w-[850px] mx-auto w-full px-4 md:px-0">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center pt-32 pb-8 text-center select-none space-y-4">
                <div className="size-16 rounded-2xl bg-surface border border-border/50 flex items-center justify-center text-foreground shadow-sm">
                  <Bot className="size-8" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-[30px] font-medium text-foreground tracking-tight">How can I help you today?</h3>
                </div>
              </div>
            ) : (
              <div className="flex flex-col pt-8">
                {messages.map((msg) => (
                  <MessageItem key={msg.message_id} message={msg} />
                ))}
                
                {isLoadingMessages && (
                  <div className="w-full flex justify-start px-4 py-6 md:px-0 group select-text gap-4">
                    <div className="size-8 rounded-lg bg-surface border border-border/50 flex items-center justify-center shrink-0 mt-1 shadow-sm">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary animate-pulse"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                    </div>
                    <div className="flex-1 max-w-full space-y-2 min-w-0 mt-1.5 flex flex-col items-start">
                      <div className="flex items-center gap-3">
                        <span className="text-[14px] font-medium text-muted-foreground animate-pulse">
                          {loadingStep === 0 ? "Searching Documents..." : loadingStep === 1 ? "Retrieving Context..." : "Generating Answer..."}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={chatEndRef} />
              </div>
            )}
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-background via-background/95 to-transparent pt-12 shrink-0 select-none">
          <div className="max-w-[850px] mx-auto relative">
            <div className="relative bg-surface border border-border/80 hover:border-border rounded-2xl shadow-sm flex flex-col focus-within:border-border transition-colors">
              <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                accept=".pdf" 
                onChange={handleFileChange} 
              />
              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about your documents..."
                disabled={isLoadingMessages}
                className="w-full resize-none bg-transparent pt-4 pb-14 px-4 text-[16px] text-foreground placeholder-muted-foreground outline-none font-sans min-h-[56px] max-h-[144px] overflow-y-auto disabled:opacity-50"
              />

              <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between shrink-0 select-none">
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleUploadClick}
                    className="size-8 text-muted-foreground hover:text-foreground rounded-lg hover:bg-card cursor-pointer"
                    title="Attach PDF"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {}}
                    className="size-8 text-muted-foreground hover:text-foreground rounded-lg hover:bg-card cursor-pointer hidden md:flex"
                    title="Library"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
                  </Button>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-muted-foreground hidden md:inline-block font-medium">
                    <kbd className="font-sans px-1 py-0.5 rounded-sm bg-card border border-border/50">Enter</kbd> to send, <kbd className="font-sans px-1 py-0.5 rounded-sm bg-card border border-border/50">Shift + Enter</kbd> for new line
                  </span>
                  {isLoadingMessages ? (
                    <Button
                      onClick={() => {
                        // Normally this would abort the fetch.
                        // Mocking behavior to respect "No backend breaking changes"
                      }}
                      className="size-8 bg-surface border border-border text-foreground hover:bg-muted rounded-lg cursor-pointer flex items-center justify-center p-0 transition-colors shadow-sm"
                    >
                      <Square className="size-3.5 fill-current" />
                    </Button>
                  ) : (
                    <Button
                      onClick={handleSend}
                      disabled={!input.trim()}
                      className="size-8 bg-primary hover:bg-primary/90 text-primary-foreground disabled:opacity-40 disabled:bg-primary/50 rounded-lg cursor-pointer flex items-center justify-center p-0 transition-colors shadow-sm"
                    >
                      <Send className="size-4 ml-0.5" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
            
            <div className="text-center mt-3">
              <span className="text-[11px] text-muted-foreground">
                IntelChat can make mistakes. Consider verifying important information.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
