"use client"

import * as React from "react"
import Link from "next/link"
import { Search, Filter, Calendar, MessageSquare, ArrowRight, CornerDownRight } from "lucide-react"
import { Card } from "@/components/ui/Card"
import { Input } from "@/components/ui/Input"
import { EmptyState } from "@/components/ui/EmptyState"
import { useSessionStore } from "@/store/useSessionStore"
import { toast } from "sonner"
import { searchApi } from "@/services/api"
import { SearchMatch } from "@/types"

export function GlobalSearch() {
  const [query, setQuery] = React.useState("")
  const [isSearching, setIsSearching] = React.useState(false)
  const [results, setResults] = React.useState<SearchMatch[]>([])
  const { setActiveSessionId } = useSessionStore()

  React.useEffect(() => {
    if (!query.trim()) {
      return
    }

    const timeout = setTimeout(async () => {
      try {
        const matches = await searchApi.search(query)
        setResults(matches)
      } catch (error) {
        console.error("Search failed:", error)
        toast.error("Search query failed")
      } finally {
        setIsSearching(false)
      }
    }, 400) // Debounce

    return () => {
      clearTimeout(timeout)
    }
  }, [query])

  // Derive empty results when query is empty, avoiding setState in useEffect
  const displayedResults = query.trim() ? results : []

  const highlightMatch = (text: string, highlight: string) => {
    if (!highlight) return text
    const parts = text.split(new RegExp(`(${highlight})`, "gi"))
    return (
      <span>
        {parts.map((part, i) =>
          part.toLowerCase() === highlight.toLowerCase() ? (
            <mark key={i} className="bg-highlight/30 text-highlight font-bold px-1 rounded-sm">
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </span>
    )
  }

  const handleSelectMatch = (sessionId: string) => {
    setActiveSessionId(sessionId)
    toast.info("Navigating to chat conversation...")
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar space-y-6 max-w-4xl mx-auto">
      {/* Search inputs */}
      <div className="space-y-4 select-none">
        <div className="relative w-full">
          <Input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              if (e.target.value.trim()) {
                setIsSearching(true)
              }
            }}
            placeholder="Type keywords to search message history (FTS5 enabled)..."
            className="pl-12 h-12 text-base rounded-2xl bg-card border-border/80"
            autoFocus
          />
          <Search className="size-5 text-muted-foreground absolute left-4.5 top-3.5" />
        </div>

        {/* Filters placeholder */}
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground font-semibold">
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/60 bg-surface/40 hover:bg-surface cursor-pointer">
            <Filter className="size-3.5" /> All Sessions
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/60 bg-surface/40 hover:bg-surface cursor-pointer">
            <Calendar className="size-3.5" /> Any Time
          </button>
        </div>
      </div>

      {/* Query results section */}
      <div className="space-y-4">
        {isSearching ? (
          <div className="space-y-4">
            {[1, 2].map((i) => (
              <Card key={i} className="p-4 border-border bg-card/20 space-y-2 animate-pulse">
                <div className="h-4 w-1/4 bg-border rounded" />
                <div className="h-3 w-3/4 bg-border rounded" />
              </Card>
            ))}
          </div>
        ) : query.trim() && displayedResults.length === 0 ? (
          <EmptyState type="no-search-results" className="py-16" />
        ) : !query.trim() ? (
          <div className="py-16 text-center select-none space-y-3">
            <div className="size-12 rounded-xl bg-card border border-border/60 flex items-center justify-center text-muted-foreground mx-auto">
              <Search className="size-5 text-highlight" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-foreground">Global Search Shell</h4>
              <p className="text-xs text-secondary-foreground max-w-sm mx-auto">
                Type above to match keywords across your RAG conversations using the SQLite FTS5 full-text index.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4 select-none">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
              Found {displayedResults.length} Matches
            </span>
            <div className="space-y-3">
              {displayedResults.map((match) => (
                <Card
                  key={match.message_id}
                  variant="interactive"
                  onClick={() => handleSelectMatch(match.session_id)}
                  className="p-5 border-border/80 bg-card/30 hover:bg-card/50 transition-all duration-300 flex flex-col justify-between cursor-pointer"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                        <MessageSquare className="size-4 text-highlight" />
                        <span>{match.session_title}</span>
                      </div>
                      <span className="text-[9px] text-muted-foreground">
                        {new Date(match.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                    
                    <div className="flex items-start gap-1.5 text-xs text-secondary-foreground leading-relaxed pl-1">
                      <CornerDownRight className="size-3.5 text-muted-foreground shrink-0 mt-0.5" />
                      <p className="italic">
                        &quot;{highlightMatch(match.content, query)}&quot;
                      </p>
                    </div>
                  </div>

                  <Link href={`/?session=${match.session_id}`} onClick={(e) => e.stopPropagation()} className="self-end mt-3 text-[10px] text-highlight font-semibold flex items-center gap-1 hover:underline">
                    View Conversation <ArrowRight className="size-3" />
                  </Link>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
