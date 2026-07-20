"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { Sun, Moon, Laptop, Menu, Settings, FileText } from "lucide-react"
import { useUIStore } from "@/store/useUIStore"
import { useUploadStore } from "@/store/useUploadStore"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu"

export function Header() {
  const { theme, setTheme } = useTheme()
  const { isSidebarOpen, setSidebarOpen, setSettingsOpen } = useUIStore()
  const { documents, selectedDocumentId } = useUploadStore()
  const [mounted, setMounted] = React.useState(false)

  const selectedDoc = documents.find(d => d.document_id === selectedDocumentId)

  React.useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 0)
    return () => clearTimeout(timer)
  }, [])

  return (
    <header className="sticky top-0 z-30 w-full bg-background px-4 sm:px-6 h-14 flex items-center justify-between">
      {/* Left side: Mobile Drawer Toggler & Title */}
      <div className="flex items-center gap-3">
        {/* Hamburger toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSidebarOpen(!isSidebarOpen)}
          className="size-9 text-muted-foreground hover:text-foreground cursor-pointer -ml-2"
          aria-label="Toggle Navigation Drawer"
        >
          <Menu className="size-5" />
        </Button>

        {/* Title and Document */}
        <div className="flex items-center gap-3">
          <span className="font-semibold text-[15px] text-foreground tracking-tight hidden md:inline-block">
            IntelChat
          </span>
          {selectedDoc && (
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-primary/10 border border-primary/20 text-[12px] font-medium text-primary select-none max-w-[200px]">
              <FileText className="size-3.5 shrink-0" />
              <span className="truncate">{selectedDoc.original_filename}</span>
            </div>
          )}
        </div>
      </div>

      {/* Right side: Tools + settings + theme */}
      <div className="flex items-center gap-1">
        {/* Theme Toggle Dropdown */}
        {mounted && (
          <DropdownMenu>
            <Tooltip>
              <TooltipTrigger
                render={
                  <DropdownMenuTrigger
                    render={
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground hover:bg-surface hover:text-foreground cursor-pointer rounded-lg"
                        aria-label="Select theme options"
                      >
                        {theme === "dark" ? (
                          <Moon className="size-4 transition-all" />
                        ) : theme === "light" ? (
                          <Sun className="size-4 transition-all" />
                        ) : (
                          <Laptop className="size-4 transition-all" />
                        )}
                      </Button>
                    }
                  />
                }
              />
              <TooltipContent>Theme options</TooltipContent>
            </Tooltip>

            <DropdownMenuContent align="end" className="w-36 bg-surface border-border/80 rounded-xl shadow-sm">
              <DropdownMenuItem onClick={() => setTheme("dark")} className="flex items-center gap-2 text-[12px] text-foreground cursor-pointer focus:bg-sidebar-accent">
                <Moon className="size-3.5" /> Dark
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("light")} className="flex items-center gap-2 text-[12px] text-foreground cursor-pointer focus:bg-sidebar-accent">
                <Sun className="size-3.5" /> Light
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("system")} className="flex items-center gap-2 text-[12px] text-foreground cursor-pointer focus:bg-sidebar-accent">
                <Laptop className="size-3.5" /> System
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Settings Toggle Shortcut */}
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSettingsOpen(true)}
                className="size-8 text-muted-foreground hover:bg-surface hover:text-foreground cursor-pointer rounded-lg"
              >
                <Settings className="size-4" />
              </Button>
            }
          />
          <TooltipContent>Settings</TooltipContent>
        </Tooltip>
      </div>
    </header>
  )
}
