"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { Moon, Sun, Laptop, Trash2, Settings as SettingsIcon } from "lucide-react"
import { useUIStore } from "@/store/useUIStore"
import { useSessionStore } from "@/store/useSessionStore"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/Switch"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { toast } from "sonner"

export function SettingsDrawer() {
  const { theme, setTheme } = useTheme()
  const { settingsOpen, setSettingsOpen } = useUIStore()
  const { sessions, deleteSession } = useSessionStore()
  
  // Local state for mocked settings
  const [model, setModel] = React.useState("qwen2.5:7b")
  const [temperature, setTemperature] = React.useState(0.2)
  const [streaming, setStreaming] = React.useState(true)

  const handleClearHistory = async () => {
    if (confirm("Are you sure you want to delete all chat conversations? This cannot be undone.")) {
      try {
        for (const s of sessions) {
          await deleteSession(s.session_id)
        }
        toast.success("All conversations cleared")
        setSettingsOpen(false)
      } catch {
        toast.error("Failed to clear conversations")
      }
    }
  }

  return (
    <Sheet open={settingsOpen} onOpenChange={setSettingsOpen}>
      <SheetContent className="w-full sm:max-w-md bg-surface border-l border-border text-foreground p-6 overflow-y-auto flex flex-col justify-between z-50">
        <div className="space-y-8">
          <SheetHeader className="pb-4 border-b border-border/40">
            <SheetTitle className="text-xl font-heading flex items-center gap-2">
              <SettingsIcon className="size-5" />
              Settings
            </SheetTitle>
            <SheetDescription className="text-muted-foreground text-[14px]">
              Configure your IntelChat preferences.
            </SheetDescription>
          </SheetHeader>

          {/* Theme */}
          <div className="space-y-4">
            <h3 className="text-[14px] font-medium text-foreground">Theme</h3>
            <div className="grid grid-cols-3 gap-2">
              <Button
                variant={theme === "light" ? "secondary" : "outline"}
                className={`h-9 gap-2 font-normal rounded-lg border-border/60 ${theme === 'light' ? 'bg-card' : 'bg-transparent hover:bg-card/50'}`}
                onClick={() => setTheme("light")}
              >
                <Sun className="size-4" /> Light
              </Button>
              <Button
                variant={theme === "dark" ? "secondary" : "outline"}
                className={`h-9 gap-2 font-normal rounded-lg border-border/60 ${theme === 'dark' ? 'bg-card' : 'bg-transparent hover:bg-card/50'}`}
                onClick={() => setTheme("dark")}
              >
                <Moon className="size-4" /> Dark
              </Button>
              <Button
                variant={theme === "system" ? "secondary" : "outline"}
                className={`h-9 gap-2 font-normal rounded-lg border-border/60 ${theme === 'system' ? 'bg-card' : 'bg-transparent hover:bg-card/50'}`}
                onClick={() => setTheme("system")}
              >
                <Laptop className="size-4" /> System
              </Button>
            </div>
          </div>

          {/* Model */}
          <div className="space-y-4 pt-6 border-t border-border/40">
            <h3 className="text-[14px] font-medium text-foreground">Model Configuration</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-[13px] text-muted-foreground block">Language Model</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full h-10 px-3 bg-card border border-border/60 rounded-lg text-[14px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                >
                  <option value="qwen2.5:3b">qwen2.5:3b (Fast)</option>
                  <option value="qwen2.5:7b">qwen2.5:7b (Recommended)</option>
                </select>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[13px] text-muted-foreground">Temperature</label>
                  <span className="text-[12px] text-foreground font-mono">{temperature.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-primary h-1 bg-border rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div className="pt-2">
                <Switch
                  checked={streaming}
                  onChange={setStreaming}
                  label="Response Streaming"
                  className="peer-checked:bg-primary"
                />
              </div>
            </div>
          </div>

          {/* Data */}
          <div className="space-y-4 pt-6 border-t border-border/40">
            <h3 className="text-[14px] font-medium text-foreground">Data Management</h3>
            <Button
              variant="outline"
              onClick={handleClearHistory}
              className="w-full h-10 gap-2 rounded-lg text-[14px] font-normal border-error/50 text-error hover:bg-error/10 hover:text-error"
            >
              <Trash2 className="size-4" />
              Clear Conversations
            </Button>
          </div>
        </div>

        {/* About */}
        <div className="mt-8 pt-6 border-t border-border/40 text-center space-y-3">
          <div className="flex flex-col items-center justify-center gap-1 text-foreground">
            <span className="text-[14px] font-semibold tracking-tight">Created By</span>
            <span className="text-[15px] font-medium text-primary">Mohan Kumar</span>
          </div>
          <div className="flex items-center justify-center gap-4 pt-2">
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              <svg className="size-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
            </a>
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              <svg className="size-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" clipRule="evenodd" />
              </svg>
            </a>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
