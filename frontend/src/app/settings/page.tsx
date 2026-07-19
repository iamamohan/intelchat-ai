"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { Moon, Sun, Laptop, Trash2, Sliders, Info, ShieldAlert, Type } from "lucide-react"
import { useUIStore, FontSize } from "@/store/useUIStore"
import { useSettingsStore } from "@/store/useSettingsStore"
import { useSessionStore } from "@/store/useSessionStore"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/Switch"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card"
import { toast } from "sonner"

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { isDevMode, setDevMode, fontSize, setFontSize } = useUIStore()
  const { settings, updateSettings } = useSettingsStore()
  const { sessions } = useSessionStore()

  const handleClearHistory = () => {
    if (confirm("Are you sure you want to delete all chat conversations? This cannot be undone.")) {
      toast.success("History cleared (Simulation)")
    }
  }

  const handleFontSizeChange = (size: FontSize) => {
    setFontSize(size)
    toast.success(`Font size changed to ${size}`)
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar space-y-6 max-w-2xl mx-auto">
      <Card className="border-border bg-card/30 p-6 select-none">
        <CardHeader className="p-0 pb-4 border-b border-border/40">
          <CardTitle className="text-base font-heading flex items-center gap-2">
            <Sliders className="size-5 text-highlight" /> Core settings
          </CardTitle>
          <CardDescription className="text-xs text-muted-foreground">
            Manage your IntelChat workspace configurations.
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0 pt-6 space-y-6">
          {/* Typography options */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold flex items-center gap-2 text-foreground">
              <Type className="size-4 text-highlight" /> Typography Size
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {(["sm", "base", "lg"] as FontSize[]).map((size) => (
                <Button
                  key={size}
                  variant={fontSize === size ? "primary" : "outline"}
                  size="sm"
                  className="h-9 capitalize rounded-xl text-xs font-semibold"
                  onClick={() => handleFontSizeChange(size)}
                >
                  {size === "base" ? "Normal" : size}
                </Button>
              ))}
            </div>
          </div>

          {/* Dev Mode toggle */}
          <div className="space-y-3 pt-4 border-t border-border/20">
            <h3 className="text-xs font-semibold flex items-center gap-2 text-foreground">
              <Info className="size-4 text-highlight" /> Developer preferences
            </h3>
            <div className="space-y-3">
              <Switch
                checked={isDevMode}
                onChange={setDevMode}
                label="Developer Mode"
              />
              <p className="text-[10px] text-muted-foreground pl-11">
                Toggles retrieval confidence and RAG vectors citation scores inside feeds.
              </p>
              
              <Switch
                checked={settings.autoScroll}
                onChange={(checked) => updateSettings({ autoScroll: checked })}
                label="Auto-scroll to bottom"
              />
            </div>
          </div>

          {/* Theme Settings */}
          <div className="space-y-3 pt-4 border-t border-border/20">
            <h3 className="text-xs font-semibold flex items-center gap-2 text-foreground">
              <Sun className="size-4 text-highlight" /> Color Theme Options
            </h3>
            <div className="grid grid-cols-3 gap-2">
              <Button
                variant={theme === "light" ? "primary" : "outline"}
                size="sm"
                className="h-9 gap-1.5 rounded-xl text-xs font-semibold"
                onClick={() => setTheme("light")}
              >
                <Sun className="size-3.5" /> Light Theme
              </Button>
              <Button
                variant={theme === "dark" ? "primary" : "outline"}
                size="sm"
                className="h-9 gap-1.5 rounded-xl text-xs font-semibold"
                onClick={() => setTheme("dark")}
              >
                <Moon className="size-3.5" /> Dark Theme
              </Button>
              <Button
                variant={theme === "system" ? "primary" : "outline"}
                size="sm"
                className="h-9 gap-1.5 rounded-xl text-xs font-semibold"
                onClick={() => setTheme("system")}
              >
                <Laptop className="size-3.5" /> System Default
              </Button>
            </div>
          </div>

          {/* Danger zone actions */}
          <div className="space-y-3 pt-4 border-t border-border/20">
            <h3 className="text-xs font-semibold flex items-center gap-2 text-error">
              <ShieldAlert className="size-4" /> Danger Zone
            </h3>
            <Button
              variant="danger"
              onClick={handleClearHistory}
              className="w-full h-10 gap-2 rounded-xl text-xs font-semibold"
            >
              <Trash2 className="size-4" /> Clear All Chat Sessions ({sessions.length})
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
