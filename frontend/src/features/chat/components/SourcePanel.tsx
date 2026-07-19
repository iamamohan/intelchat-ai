"use client"

import * as React from "react"
import { FileText, ChevronDown, ChevronUp, AlertCircle, BarChart2 } from "lucide-react"
import { Citation } from "@/types"
import { Card } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface SourcePanelProps {
  citations: Citation[];
}

export function SourcePanel({ citations = [] }: SourcePanelProps) {
  const [expandedIndex, setExpandedIndex] = React.useState<number | null>(null)

  const toggleExpand = (idx: number) => {
    setExpandedIndex((prev) => (prev === idx ? null : idx))
  }

  return (
    <div className="w-full h-full flex flex-col bg-surface border-l border-border select-none">
      {/* Panel Title */}
      <div className="h-16 px-4 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <BarChart2 className="size-4.5 text-highlight" />
          <span className="font-heading font-semibold text-sm text-foreground">
            Retrieved Context Sources
          </span>
        </div>
        <Badge variant="outline" size="sm">
          {citations.length} Cited
        </Badge>
      </div>

      {/* Sources list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {citations.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-3 p-4">
            <div className="p-3 bg-card border border-border/60 rounded-xl text-muted-foreground">
              <AlertCircle className="size-5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-foreground">No citations for this turn</p>
              <p className="text-[10px] text-muted-foreground max-w-[200px] mt-1 leading-normal">
                Ask a question to see the RAG retrieval chunks and scores in this panel.
              </p>
            </div>
          </div>
        ) : (
          citations.map((cit, idx) => {
            const isExpanded = expandedIndex === idx
            const percentage = (cit.similarity_score * 100).toFixed(0)

            return (
              <Card
                key={idx}
                variant="interactive"
                className="overflow-hidden border border-border/80 bg-card/40 p-4 space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div className="p-2 rounded-lg bg-surface border border-border/60 text-highlight shrink-0 mt-0.5">
                      <FileText className="size-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-foreground truncate max-w-[150px]">
                        {cit.document_name}
                      </p>
                      <p className="text-[10px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                        <span>Page {cit.page_number}</span>
                        <span>•</span>
                        <span>Chunk #{cit.chunk_id}</span>
                      </p>
                    </div>
                  </div>

                  <Badge
                    variant={cit.similarity_score > 0.8 ? "success" : "highlight"}
                    size="sm"
                    className="font-bold text-[8px] tracking-wider"
                  >
                    {percentage}% Match
                  </Badge>
                </div>

                {/* Snippet Preview */}
                <div className="relative">
                  <p
                    className={cn(
                      "text-[11px] text-secondary-foreground leading-relaxed transition-all duration-200",
                      !isExpanded && "line-clamp-3"
                    )}
                  >
                    &quot;{cit.snippet_text || "Source context retrieved from document index. This represents the segment parsed and vectorized during Sprint 9 pipeline execution."}&quot;
                  </p>
                </div>

                {/* Toggler button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleExpand(idx)}
                  className="w-full h-8 justify-center gap-1.5 text-[10px] font-semibold border border-border/40 hover:bg-surface/60 rounded-lg"
                >
                  {isExpanded ? (
                    <>
                      <span>Collapse Source</span>
                      <ChevronUp className="size-3" />
                    </>
                  ) : (
                    <>
                      <span>Expand Full Context</span>
                      <ChevronDown className="size-3" />
                    </>
                  )}
                </Button>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
