"use client"

import { create } from "zustand"

export type FontSize = "sm" | "base" | "lg"

interface UIState {
  isSidebarOpen: boolean;
  isDevMode: boolean;
  fontSize: FontSize;
  activeSessionId: string | null;
  settingsOpen: boolean;
  
  // Actions
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setDevMode: (dev: boolean) => void;
  toggleDevMode: () => void;
  setFontSize: (size: FontSize) => void;
  setActiveSessionId: (id: string | null) => void;
  setSettingsOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isSidebarOpen: true,
  isDevMode: false,
  fontSize: "base",
  activeSessionId: null,
  settingsOpen: false,

  setSidebarOpen: (open) => set({ isSidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setDevMode: (dev) => set({ isDevMode: dev }),
  toggleDevMode: () => set((state) => ({ isDevMode: !state.isDevMode })),
  setFontSize: (size) => set({ fontSize: size }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  setSettingsOpen: (open) => set({ settingsOpen: open }),
}))
