"use client"

import * as React from "react"
import { Database, Clock, Cpu, LayoutGrid, Award, HardDrive, MessageSquare } from "lucide-react"
import { Card } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Spinner } from "@/components/ui/Spinner"
import { statisticsApi } from "@/services/api"
import { Statistics } from "@/types"

export function StatsDashboard() {
  const [stats, setStats] = React.useState<Statistics | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)

  React.useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await statisticsApi.getStatistics()
        setStats(data)
      } catch (error) {
        console.error("Failed to load statistics:", error)
      } finally {
        setIsLoading(false)
      }
    }
    fetchStats()
  }, [])

  if (isLoading || !stats) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 select-none">
        <div className="flex flex-col items-center gap-2">
          <Spinner size="lg" variant="accent" />
          <span className="text-xs text-muted-foreground">Gathering knowledge base metrics...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar space-y-8 select-none max-w-5xl mx-auto animate-in fade-in-0 duration-200">
      {/* Overview Grid Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Documents", value: stats.total_documents ?? 0, icon: Database },
          { label: "Total Chunks", value: stats.total_chunks ?? 0, icon: LayoutGrid },
          { label: "Vector Embeddings", value: stats.total_embeddings ?? 0, icon: Cpu },
          { label: "Storage Used", value: `${stats.storage_used_mb ?? 0} MB`, icon: HardDrive },
        ].map((item, idx) => {
          const Icon = item.icon
          return (
            <Card key={idx} className="p-5 border-border/80 bg-card/30 flex flex-col justify-between h-28">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
                {item.label}
              </span>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xl font-heading font-extrabold text-foreground">{item.value}</span>
                <div className="p-2 rounded-lg bg-surface border border-border/60 text-highlight">
                  <Icon className="size-4" />
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Speed Metrics & Chart Display */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Metric list cards */}
        <Card className="p-5 border-border/80 bg-card/30 md:col-span-1 space-y-4 flex flex-col justify-between">
          <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">Speed Averages</h3>
          <div className="space-y-3.5 text-xs text-secondary-foreground font-medium pl-1">
            <div className="flex justify-between">
              <span className="flex items-center gap-1.5"><Clock className="size-3.5 text-muted-foreground" /> Retrieval time</span>
              <span className="text-foreground font-bold">{(stats.average_retrieval_time_seconds ?? 0).toFixed(3)}s</span>
            </div>
            <div className="flex justify-between">
              <span className="flex items-center gap-1.5"><Clock className="size-3.5 text-muted-foreground" /> Response time</span>
              <span className="text-foreground font-bold">{(stats.average_chat_time_seconds ?? 0).toFixed(3)}s</span>
            </div>
            <div className="flex justify-between">
              <span className="flex items-center gap-1.5"><Clock className="size-3.5 text-muted-foreground" /> Embedding speed</span>
              <span className="text-foreground font-bold">{(stats.average_embedding_time_seconds ?? 0).toFixed(3)}s</span>
            </div>
          </div>
          <div className="pt-3 border-t border-border/20 flex items-center justify-between text-[10px] text-muted-foreground">
            <span>RAG Context Cache</span>
            <Badge variant="success" size="sm">Enabled</Badge>
          </div>
        </Card>

        {/* Minimal Dark SVG Chart (simulating workspace queries) */}
        <Card className="p-5 border-border/80 bg-card/30 md:col-span-2 space-y-4 flex flex-col justify-between">
          <div className="flex justify-between items-center select-none">
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">Workspace Queries Load</h3>
            <span className="text-[10px] text-muted-foreground font-medium">Last 8 Days</span>
          </div>

          {/* SVG line graph */}
          <div className="h-32 w-full flex items-end justify-center pt-2 relative">
            <svg className="w-full h-full text-highlight overflow-visible" viewBox="0 0 100 30" preserveAspectRatio="none">
              <path
                d="M0,25 Q15,10 30,18 T60,5 T90,20 T100,8"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className="opacity-90"
              />
              <path
                d="M0,25 Q15,10 30,18 T60,5 T90,20 T100,8 L100,30 L0,30 Z"
                fill="url(#grad)"
                className="opacity-5"
              />
              <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="currentColor" />
                  <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
                </linearGradient>
              </defs>
            </svg>
            
            {/* SVG coordinates grid bars */}
            <div className="absolute inset-0 flex justify-between pointer-events-none opacity-20 border-b border-border/40">
              <div className="border-r border-border/40 h-full w-[1px]" />
              <div className="border-r border-border/40 h-full w-[1px]" />
              <div className="border-r border-border/40 h-full w-[1px]" />
              <div className="border-r border-border/40 h-full w-[1px]" />
            </div>
          </div>

          <div className="flex justify-between text-[8px] text-muted-foreground font-bold tracking-wider uppercase pt-2 border-t border-border/20 select-none">
            <span>July 9</span>
            <span>July 11</span>
            <span>July 13</span>
            <span>July 15</span>
          </div>
        </Card>
      </div>

      {/* Conversation Metrics & Quality */}
      <Card className="p-5 border-border/80 bg-card/30 space-y-4">
        <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">Quality Indices</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          {[
            { label: "Active Sessions", value: stats.chat_analytics?.total_sessions ?? 0, icon: MessageSquare },
            { label: "LLM Provider", value: stats.llm_provider ?? "Gemini", icon: Cpu },
            { label: "Embedding Model", value: "MiniLM-L6", icon: Award },
            { label: "Total Messages", value: stats.chat_analytics?.total_messages ?? 0, icon: Database },
          ].map((item, idx) => {
            const Icon = item.icon
            return (
              <div key={idx} className="p-4 rounded-2xl bg-surface/50 border border-border/40 flex flex-col items-center justify-center space-y-2">
                <Icon className="size-4.5 text-highlight" />
                <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">{item.label}</span>
                <span className="text-sm font-heading font-extrabold text-foreground">{item.value}</span>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
