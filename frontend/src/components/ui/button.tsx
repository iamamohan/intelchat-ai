import * as React from "react"
import { cn } from "@/lib/utils"
import { LucideLoader2 } from "lucide-react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "success";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex shrink-0 items-center justify-center rounded-xl border border-transparent font-medium whitespace-nowrap transition-all duration-200 outline-none select-none active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 cursor-pointer",
          // Focus state
          "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          // Variants
          variant === "primary" && "bg-primary text-primary-foreground hover:bg-primary/90",
          variant === "secondary" && "bg-surface text-secondary-foreground hover:bg-border/60 border-border/40",
          variant === "outline" && "border-border bg-transparent hover:bg-surface text-foreground",
          variant === "ghost" && "hover:bg-surface hover:text-foreground text-secondary-foreground",
          variant === "danger" && "bg-error text-primary-foreground hover:bg-error/90",
          variant === "success" && "bg-success text-primary-foreground hover:bg-success/90",
          // Sizes
          size === "sm" && "h-9 px-3.5 text-xs gap-1.5",
          size === "md" && "h-11 px-5 text-sm gap-2",
          size === "lg" && "h-13 px-7 text-base gap-2.5",
          size === "icon" && "size-10 p-0 text-sm",
          className
        )}
        {...props}
      >
        {isLoading ? (
          <>
            <LucideLoader2 className="size-4 animate-spin text-current" />
            {size !== "icon" && <span>Loading...</span>}
          </>
        ) : (
          children
        )}
      </button>
    )
  }
)

Button.displayName = "Button"

export { Button }
