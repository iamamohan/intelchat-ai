import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  variant?: "default" | "secondary" | "error";
  size?: "sm" | "md" | "lg";
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", variant = "default", size = "md", ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          "flex w-full rounded-xl border border-transparent bg-surface text-sm text-foreground transition-all duration-200 file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder-muted-foreground outline-none",
          // Focus state
          "focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring",
          // Disabled state
          "disabled:cursor-not-allowed disabled:opacity-40",
          // Variants
          variant === "default" && "bg-surface border-border/80",
          variant === "secondary" && "bg-card border-border/40",
          variant === "error" && "border-error focus-visible:border-error focus-visible:ring-error/50",
          // Sizes
          size === "sm" && "h-9 px-3 text-xs",
          size === "md" && "h-11 px-4 text-sm",
          size === "lg" && "h-13 px-5 text-base",
          className
        )}
        {...props}
      />
    )
  }
)

Input.displayName = "Input"

export { Input }
