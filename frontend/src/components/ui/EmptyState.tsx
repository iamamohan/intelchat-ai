import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "./button"
import {
  MessageSquare,
  FileText,
  Search,
  BarChart3,
  WifiOff,
  Compass,
  AlertCircle
} from "lucide-react"

export type EmptyStateType =
  | "no-chats"
  | "no-documents"
  | "no-search-results"
  | "no-statistics"
  | "offline"
  | "loading"
  | "coming-soon";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  type: EmptyStateType;
  title?: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
}

const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ className, type, title, description, actionText, onAction, ...props }, ref) => {
    // Map icons & defaults based on state type
    let DefaultIcon = Compass
    let defaultTitle = "No data found"
    let defaultDesc = "There is nothing to display here right now."

    switch (type) {
      case "no-chats":
        DefaultIcon = MessageSquare
        defaultTitle = "No conversations yet"
        defaultDesc = "Create a new conversation to start interacting with your workspace."
        break
      case "no-documents":
        DefaultIcon = FileText
        defaultTitle = "No knowledge files uploaded"
        defaultDesc = "Upload PDF handbooks, policy guides, or whitepapers to feed your RAG pipeline."
        break
      case "no-search-results":
        DefaultIcon = Search
        defaultTitle = "No matches found"
        defaultDesc = "We couldn't find any messages or files matching that search query. Try other keywords."
        break
      case "no-statistics":
        DefaultIcon = BarChart3
        defaultTitle = "Analytics unavailable"
        defaultDesc = "Upload some documents and send queries to populate the statistical dashboards."
        break
      case "offline":
        DefaultIcon = WifiOff
        defaultTitle = "Connection lost"
        defaultDesc = "You are currently offline. Please check your internet settings and try again."
        break
      case "loading":
        DefaultIcon = AlertCircle
        defaultTitle = "Loading content"
        defaultDesc = "Please wait while we index your resources and build the dashboard."
        break
      case "coming-soon":
        DefaultIcon = Compass
        defaultTitle = "Coming Soon"
        defaultDesc = "This workspace capsule feature is currently under active development."
        break
    }

    const currentTitle = title || defaultTitle
    const currentDesc = description || defaultDesc

    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center text-center p-8 rounded-2xl border border-dashed border-border/80 bg-surface/30 max-w-lg mx-auto space-y-5 select-none",
          className
        )}
        {...props}
      >
        <div className="p-4 rounded-xl bg-card border border-border/60 text-secondary-foreground animate-pulse shadow-sm">
          <DefaultIcon className="size-6 text-highlight" />
        </div>
        <div className="space-y-1.5">
          <h3 className="font-heading font-semibold text-base text-foreground tracking-tight">
            {currentTitle}
          </h3>
          <p className="text-xs text-secondary-foreground max-w-sm leading-normal">
            {currentDesc}
          </p>
        </div>
        {actionText && onAction && (
          <Button variant="outline" size="sm" onClick={onAction}>
            {actionText}
          </Button>
        )}
      </div>
    )
  }
)

EmptyState.displayName = "EmptyState"

export { EmptyState }
