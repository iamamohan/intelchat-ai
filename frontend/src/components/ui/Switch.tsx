import * as React from "react"
import { cn } from "@/lib/utils"

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  label?: string;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, checked, onChange, label, disabled, ...props }, ref) => {
    const id = React.useId()
    
    const handleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(e.target.checked)
    }

    return (
      <div className="flex items-center space-x-2 select-none">
        <label htmlFor={id} className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            id={id}
            ref={ref}
            checked={checked}
            onChange={handleToggle}
            disabled={disabled}
            className="sr-only peer"
            {...props}
          />
          <div
            className={cn(
              "w-9 h-5 rounded-full bg-border/60 peer-checked:bg-primary transition-all duration-200 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-primary-foreground after:border-border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4 disabled:opacity-40 disabled:cursor-not-allowed",
              "peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-background",
              className
            )}
          />
        </label>
        {label && (
          <label
            htmlFor={id}
            className={cn(
              "text-sm font-medium text-secondary-foreground cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed",
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

Switch.displayName = "Switch"

export { Switch }
