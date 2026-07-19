"use client"

import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useUIStore } from "@/store/useUIStore"
import { Sidebar } from "@/components/navigation/Sidebar"
import { Header } from "@/components/navigation/Header"
import { SettingsDrawer } from "@/features/settings/components/SettingsDrawer"
import { X } from "lucide-react"

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isSidebarOpen, setSidebarOpen } = useUIStore()

  return (
    <div className="h-screen w-screen flex bg-background text-foreground overflow-hidden font-sans">
      {/* Settings Dialog Drawer mounted globally */}
      <SettingsDrawer />

      {/* Desktop Sidebar (visible on md+) */}
      <div className="hidden md:flex h-full">
        <Sidebar />
      </div>

      {/* Mobile Drawer Sidebar overlay (visible on <md) */}
      <AnimatePresence>
        {isSidebarOpen && (
          <div className="md:hidden">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSidebarOpen(false)}
              className="fixed inset-0 bg-background/80 z-40"
            />
            
            {/* Drawer */}
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 w-[280px] bg-sidebar border-r border-sidebar-border z-50 flex flex-col"
            >
              <div className="h-14 border-b border-sidebar-border flex items-center justify-between px-4 shrink-0 bg-sidebar">
                <span className="font-semibold text-[15px] tracking-tight text-sidebar-foreground">
                  Menu
                </span>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1 rounded-md text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent cursor-pointer"
                >
                  <X className="size-5" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto">
                <Sidebar />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Main Workspace (Header + Active view children) */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <Header />
        
        {/* Scrollable View Area */}
        <main className="flex-1 overflow-hidden relative flex flex-col min-h-0 bg-background">
          <AnimatePresence mode="wait">
            <motion.div
              key="main-view"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 5 }}
              transition={{ duration: 0.2 }}
              className="flex-1 flex flex-col min-h-0 overflow-hidden"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
