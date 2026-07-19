import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "secondary" | "outline" | "highlight" | "success" | "warning" | "danger";
  size?: "sm" | "md";
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center font-semibold rounded-full border tracking-wide uppercase select-none",
          // Variants
          variant === "primary" && "bg-primary/10 border-primary/20 text-foreground",
          variant === "secondary" && "bg-surface border-border/40 text-secondary-foreground",
          variant === "outline" && "border-border bg-transparent text-secondary-foreground",
          variant === "highlight" && "bg-highlight/10 border-highlight/20 text-highlight",
          variant === "success" && "bg-success/15 border-success/20 text-success",
          variant === "warning" && "bg-warning/15 border-warning/20 text-warning",
          variant === "danger" && "bg-error/15 border-error/20 text-error",
          // Sizes
          size === "sm" && "text-[9px] px-1.5 py-0.5",
          size === "md" && "text-[10px] px-2 py-0.5",
          className
        )}
        {...props}
      />
    )
  }
)

Badge.displayName = "Badge"

export { Badge }
