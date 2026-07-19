"use client"

import * as React from "react"
import Image from "next/image"
import { motion } from "framer-motion"
import { useSessionStore } from "@/store/useSessionStore"
import { FileText, AlignLeft, HelpCircle } from "lucide-react"

export function WelcomeScreen() {
  const { createSession, setActiveSessionId, loadSessions, sendMessage } = useSessionStore()

  React.useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const handlePromptClick = async (query: string) => {
    try {
      const id = await createSession(query.length > 30 ? query.substring(0, 28) + "..." : query)
      setActiveSessionId(id)
      await sendMessage(id, query)
    } catch (err) {
      console.error(err)
    }
  }

  const quickPrompts = [
    {
      title: "Explain this PDF",
      desc: "Upload a complex document and I'll break it down into simple terms.",
      query: "Can you explain the main concepts in the uploaded document?",
      icon: FileText
    },
    {
      title: "Summarize document",
      desc: "Get a quick overview of long reports or research papers.",
      query: "Please provide a concise summary of the attached document.",
      icon: AlignLeft
    },
    {
      title: "Ask about uploaded files",
      desc: "Ask specific questions to extract exactly what you need.",
      query: "Based on the uploaded files, what are the key takeaways regarding the new project?",
      icon: HelpCircle
    }
  ]

  return (
    <div className="flex-1 flex flex-col bg-background relative overflow-hidden">
      <div className="flex-1 flex flex-col items-center justify-center px-4 w-full pb-32">
        <div className="w-full max-w-[800px] flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="mb-6 relative size-20 rounded-2xl overflow-hidden flex items-center justify-center bg-surface border border-border/50 shadow-sm"
          >
            <Image src="/logo.png" alt="IntelChat Logo" width={48} height={48} className="object-contain" priority />
          </motion.div>
          
          <motion.h1
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.3 }}
            className="text-[32px] font-semibold text-foreground mb-1 tracking-tight"
          >
            IntelChat
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            className="text-[15px] text-muted-foreground mb-12"
          >
            Knowledge Assistant
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.3 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full"
          >
            {quickPrompts.map((item, idx) => (
              <motion.div
                key={idx}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handlePromptClick(item.query)}
                className="group flex flex-col justify-between h-[130px] p-5 rounded-xl bg-surface border border-border/60 hover:border-border hover:shadow-sm cursor-pointer transition-all duration-200"
              >
                <div className="text-[14px] font-medium text-foreground mb-2 flex items-center gap-2.5">
                  <div className="p-1.5 rounded-md bg-card border border-border/50 text-muted-foreground group-hover:text-foreground group-hover:bg-sidebar-accent transition-colors">
                    <item.icon className="size-4" />
                  </div>
                  {item.title}
                </div>
                <p className="text-[13px] text-muted-foreground leading-relaxed line-clamp-2">
                  {item.desc}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
