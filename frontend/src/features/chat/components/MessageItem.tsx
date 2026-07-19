"use client"

import * as React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeHighlight from "rehype-highlight"
import { motion } from "framer-motion"
import { Copy, Check, RotateCcw, Edit2 } from "lucide-react"
import { Message } from "@/types"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageItem({ message, isStreaming = false }: MessageItemProps) {
  const [copied, setCopied] = React.useState(false)
  const isAI = message.role === "assistant"

  const [displayedContent, setDisplayedContent] = React.useState("")
  const [isTyping, setIsTyping] = React.useState(false)

  React.useEffect(() => {
    if (isAI) {
      const alreadyAnimated = sessionStorage.getItem(`animated_${message.message_id}`)
      const isRecent = (Date.now() - new Date(message.timestamp).getTime()) < 10000

      if (!alreadyAnimated && isRecent) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setIsTyping(true)
        let i = 0
        const interval = setInterval(() => {
          const step = Math.floor(Math.random() * 4) + 2 // simulate natural token generation
          i += step
          if (i >= message.content.length) {
            setDisplayedContent(message.content)
            clearInterval(interval)
            setIsTyping(false)
            sessionStorage.setItem(`animated_${message.message_id}`, "true")
          } else {
            setDisplayedContent(message.content.slice(0, i))
          }
        }, 12)
        return () => clearInterval(interval)
      } else {
        setDisplayedContent(message.content)
      }
    }
  }, [isAI, message.content, message.message_id, message.timestamp])

  React.useEffect(() => {
    if (isTyping) {
      const chatContainer = document.querySelector('.custom-scrollbar')
      if (chatContainer) {
        const { scrollTop, scrollHeight, clientHeight } = chatContainer
        const isNearBottom = scrollHeight - (scrollTop + clientHeight) < 150
        if (isNearBottom) {
          chatContainer.scrollTop = scrollHeight
        }
      }
    }
  }, [displayedContent, isTyping])

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      toast.success("Message copied to clipboard")
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error("Failed to copy text")
    }
  }

  const handleRegenerate = (e: React.MouseEvent) => {
    e.stopPropagation()
    toast.info("Regeneration triggered (Preview)")
  }

  if (!isAI) {
    // Claude style User Bubble
    return (
      <motion.div
        initial={{ opacity: 0, x: 15 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className="w-full flex justify-end px-4 py-4 md:px-0 select-text group"
      >
        <div className="flex flex-col items-end gap-1 max-w-[85%]">
          <div className="bg-surface border border-border/60 text-foreground px-5 py-3.5 rounded-[22px] rounded-tr-md text-[16px] leading-relaxed whitespace-pre-wrap font-sans">
            {message.content}
          </div>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 pr-2">
            <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground" onClick={handleCopy}>
              <Copy className="size-3 mr-1" /> Copy
            </Button>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground" onClick={() => toast.info("Edit mode (Preview)")}>
              <Edit2 className="size-3 mr-1" /> Edit
            </Button>
          </div>
        </div>
      </motion.div>
    )
  }

  // Claude style Assistant text
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="w-full flex justify-start px-4 py-6 md:px-0 group select-text relative gap-4"
    >
      <div className="size-8 rounded-lg bg-surface border border-border/50 flex items-center justify-center shrink-0 mt-1 shadow-sm">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-foreground"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
      </div>
      <div className="flex-1 max-w-full space-y-2 min-w-0">
        <div className="prose prose-base dark:prose-invert max-w-none text-foreground leading-relaxed break-words font-sans text-[16px]">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              p: ({ children }) => <p className="mb-4 last:mb-0 text-foreground">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-6 mb-4 space-y-1 text-foreground">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-6 mb-4 space-y-1 text-foreground">{children}</ol>,
              li: ({ children }) => <li className="marker:text-primary">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              table: ({ children }) => (
                <div className="overflow-x-auto my-6 rounded-xl border border-border bg-transparent">
                  <table className="min-w-full divide-y divide-border text-[15px]">{children}</table>
                </div>
              ),
              thead: ({ children }) => <thead className="bg-surface">{children}</thead>,
              tbody: ({ children }) => <tbody className="divide-y divide-border/60">{children}</tbody>,
              tr: ({ children }) => <tr className="transition-all">{children}</tr>,
              th: ({ children }) => (
                <th className="px-4 py-3 text-left font-semibold text-foreground border-r border-border/40 last:border-r-0">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-4 py-3 border-r border-border/40 last:border-r-0 whitespace-nowrap text-foreground">
                  {children}
                </td>
              ),
              code: ({ className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || "")
                const inline = !match
                return inline ? (
                  <code
                    className="px-1.5 py-0.5 rounded-md bg-surface font-mono text-[14px] border border-border"
                    {...props}
                  >
                    {children}
                  </code>
                ) : (
                  <div className="relative my-6 rounded-xl border border-border overflow-hidden bg-card font-mono text-[14px]">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface text-[12px] text-muted-foreground select-none">
                      <span>{match[1].toUpperCase()}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-muted-foreground hover:text-foreground cursor-pointer"
                        onClick={() => {
                          navigator.clipboard.writeText(String(children).replace(/\n$/, ""))
                          toast.success("Code copied")
                        }}
                      >
                        <Copy className="size-3.5" />
                      </Button>
                    </div>
                    <pre className="p-4 overflow-x-auto text-[14px] leading-relaxed text-foreground/90">
                      <code>{children}</code>
                    </pre>
                  </div>
                )
              },
            }}
          >
            {displayedContent + (isTyping ? "▋" : "")}
          </ReactMarkdown>
        </div>

        {!isStreaming && !isTyping && (
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2 pt-3 select-none">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 gap-1.5 px-2.5 rounded-md text-[13px] font-medium text-muted-foreground hover:text-foreground hover:bg-surface"
            >
              {copied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
              <span>Copy</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRegenerate}
              className="h-8 gap-1.5 px-2.5 rounded-md text-[13px] font-medium text-muted-foreground hover:text-foreground hover:bg-surface"
            >
              <RotateCcw className="size-3.5" />
              <span>Regenerate</span>
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  )
}
