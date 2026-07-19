"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { ChevronDown } from "lucide-react"

interface AccordionContextType {
  activeValue: string | null;
  onToggle: (value: string) => void;
}

const AccordionContext = React.createContext<AccordionContextType | undefined>(undefined)

export interface AccordionProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string;
}

const Accordion = React.forwardRef<HTMLDivElement, AccordionProps>(
  ({ children, defaultValue = null, className, ...props }, ref) => {
    const [activeValue, setActiveValue] = React.useState<string | null>(defaultValue)

    const onToggle = React.useCallback((value: string) => {
      setActiveValue((prev) => (prev === value ? null : value))
    }, [])

    return (
      <AccordionContext.Provider value={{ activeValue, onToggle }}>
        <div ref={ref} className={cn("space-y-2", className)} {...props}>
          {children}
        </div>
      </AccordionContext.Provider>
    )
  }
)
Accordion.displayName = "Accordion"

export interface AccordionItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

const AccordionItem = React.forwardRef<HTMLDivElement, AccordionItemProps>(
  ({ className, value, children, ...props }, ref) => {
    const context = React.useContext(AccordionContext)
    if (!context) throw new Error("AccordionItem must be used inside Accordion")

    const isOpen = context.activeValue === value

    return (
      <div
        ref={ref}
        data-state={isOpen ? "open" : "closed"}
        className={cn("border-b border-border/40 pb-2 transition-all duration-200", className)}
        {...props}
      >
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child)) {
            return React.cloneElement(child as React.ReactElement<{ value?: string }>, { value })
          }
          return child
        })}
      </div>
    )
  }
)
AccordionItem.displayName = "AccordionItem"

export interface AccordionTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value?: string;
}

const AccordionTrigger = React.forwardRef<HTMLButtonElement, AccordionTriggerProps>(
  ({ className, value, children, ...props }, ref) => {
    const context = React.useContext(AccordionContext)
    if (!context) throw new Error("AccordionTrigger must be used inside Accordion")

    const isOpen = context.activeValue === value

    return (
      <button
        type="button"
        ref={ref}
        onClick={() => value && context.onToggle(value)}
        className={cn(
          "flex w-full items-center justify-between py-4 font-semibold text-sm transition-all hover:text-foreground text-secondary-foreground cursor-pointer select-none",
          isOpen && "text-foreground",
          className
        )}
        {...props}
      >
        {children}
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform duration-200",
            isOpen && "rotate-180 text-foreground"
          )}
        />
      </button>
    )
  }
)
AccordionTrigger.displayName = "AccordionTrigger"

export interface AccordionContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string;
}

const AccordionContent = React.forwardRef<HTMLDivElement, AccordionContentProps>(
  ({ className, value, children, ...props }, ref) => {
    const context = React.useContext(AccordionContext)
    if (!context) throw new Error("AccordionContent must be used inside Accordion")

    const isOpen = context.activeValue === value

    if (!isOpen) return null

    return (
      <div
        ref={ref}
        className={cn(
          "overflow-hidden text-xs text-secondary-foreground leading-normal pb-4 animate-[slideDown_0.2s_ease-out]",
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
AccordionContent.displayName = "AccordionContent"

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
