"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import { AppSettings } from "@/types"

interface SettingsState {
  settings: AppSettings;
  updateSettings: (updates: Partial<AppSettings>) => void;
  resetSettings: () => void;
}

const DEFAULT_SETTINGS: AppSettings = {
  theme: "dark",
  isDevMode: false,
  fontSize: "base",
  autoScroll: true,
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,
      updateSettings: (updates) => set((state) => ({
        settings: { ...state.settings, ...updates }
      })),
      resetSettings: () => set({ settings: DEFAULT_SETTINGS }),
    }),
    {
      name: "intelchat-settings-store",
    }
  )
)
