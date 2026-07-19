import * as React from "react"
import { cn } from "@/lib/utils"

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: "default" | "secondary" | "error";
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "flex min-h-[80px] w-full rounded-xl border border-transparent bg-surface px-4 py-3 text-sm text-foreground placeholder-muted-foreground outline-none transition-all duration-200 resize-y",
          // Focus state
          "focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring",
          // Disabled state
          "disabled:cursor-not-allowed disabled:opacity-40",
          // Variants
          variant === "default" && "bg-surface border-border/80",
          variant === "secondary" && "bg-card border-border/40",
          variant === "error" && "border-error focus-visible:border-error focus-visible:ring-error/50",
          className
        )}
        {...props}
      />
    )
  }
)

Textarea.displayName = "Textarea"

export { Textarea }
