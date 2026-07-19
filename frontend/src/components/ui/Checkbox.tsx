import * as React from "react"
import { cn } from "@/lib/utils"

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, disabled, ...props }, ref) => {
    const id = React.useId()
    return (
      <div className="flex items-center space-x-2 select-none">
        <div className="relative flex items-center">
          <input
            type="checkbox"
            id={id}
            ref={ref}
            disabled={disabled}
            className={cn(
              "peer size-4.5 rounded-lg border border-border bg-surface text-foreground transition-all duration-200 outline-none appearance-none checked:bg-primary checked:border-primary cursor-pointer disabled:cursor-not-allowed disabled:opacity-40",
              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              className
            )}
            {...props}
          />
          <svg
            className="absolute left-1/2 top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 pointer-events-none stroke-primary-foreground stroke-[3] fill-none opacity-0 peer-checked:opacity-100 transition-opacity"
            viewBox="0 0 24 24"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        {label && (
          <label
            htmlFor={id}
            className={cn(
              "text-sm font-medium text-secondary-foreground cursor-pointer peer-disabled:cursor-not-allowed peer-disabled:opacity-40",
              disabled && "opacity-40 cursor-not-allowed"
            )}
          >
            {label}
          </label>
        )}
      </div>
    )
  }
)

Checkbox.displayName = "Checkbox"

export { Checkbox }
