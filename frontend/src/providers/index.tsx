"use client"

import * as React from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider as NextThemesProvider } from "next-themes"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "sonner"

// Suppress the React 19 "script tag" warning in development caused by next-themes
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  const originalConsoleError = console.error
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === 'string' && args[0].includes('Encountered a script tag')) {
      return
    }
    originalConsoleError.apply(console, args)
  }
}

export function AppProviders({ children }: { children: React.ReactNode }) {
  // Safe client mounting check to prevent hydration flicker
  const [mounted, setMounted] = React.useState(false)
  
  const [queryClient] = React.useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: false,
        staleTime: 60 * 1000,
      },
    },
  }))

  React.useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 0)
    return () => clearTimeout(timer)
  }, [])

  // Defer rendering until client-side mount is complete to avoid SSR/CSR mismatches and reload loops
  if (!mounted) {
    return (
      <div className="h-screen w-screen bg-[#050505] flex items-center justify-center" aria-hidden="true" />
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <NextThemesProvider
        attribute="class"
        defaultTheme="dark"
        enableSystem={true}
        disableTransitionOnChange
      >
        <TooltipProvider delay={200}>
          {children}
          <Toaster 
            position="bottom-right" 
            theme="dark" 
            richColors 
            closeButton
            toastOptions={{
              className: "bg-card text-foreground border border-border rounded-xl",
            }}
          />
        </TooltipProvider>
      </NextThemesProvider>
    </QueryClientProvider>
  )
}
