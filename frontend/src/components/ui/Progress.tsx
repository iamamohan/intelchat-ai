import * as React from "react"
import { cn } from "@/lib/utils"

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; // 0 to 100
  variant?: "primary" | "success" | "warning" | "danger";
  size?: "sm" | "md";
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, variant = "primary", size = "sm", ...props }, ref) => {
    // Clamp value between 0 and 100
    const clampedValue = Math.min(Math.max(value, 0), 100)

    return (
      <div
        ref={ref}
        className={cn(
          "w-full bg-border/40 rounded-full overflow-hidden",
          size === "sm" && "h-1.5",
          size === "md" && "h-2.5",
          className
        )}
        role="progressbar"
        aria-valuenow={clampedValue}
        aria-valuemin={0}
        aria-valuemax={100}
        {...props}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300 ease-out",
            variant === "primary" && "bg-primary",
            variant === "success" && "bg-success",
            variant === "warning" && "bg-warning",
            variant === "danger" && "bg-error"
          )}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    )
  }
)

Progress.displayName = "Progress"

export { Progress }
