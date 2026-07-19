import * as React from "react"
import { cn } from "@/lib/utils"
import { LucideLoader2 } from "lucide-react"

export interface SpinnerProps extends React.HTMLAttributes<SVGSVGElement> {
  size?: "sm" | "md" | "lg";
  variant?: "primary" | "secondary" | "accent";
}

const Spinner = React.forwardRef<SVGSVGElement, SpinnerProps>(
  ({ className, size = "md", variant = "primary", ...props }, ref) => {
    return (
      <LucideLoader2
        ref={ref}
        className={cn(
          "animate-spin shrink-0",
          size === "sm" && "size-4",
          size === "md" && "size-6",
          size === "lg" && "size-8",
          variant === "primary" && "text-foreground",
          variant === "secondary" && "text-secondary-foreground",
          variant === "accent" && "text-highlight",
          className
        )}
        {...props}
      />
    )
  }
)

Spinner.displayName = "Spinner"

export { Spinner }
