"use client"

import * as React from "react"
import Link from "next/link"
import { Compass } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function NotFound() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-6 space-y-6 select-none bg-background">
      <div className="p-4 rounded-2xl bg-card border border-border/80 text-highlight animate-bounce shadow-sm">
        <Compass className="size-10" />
      </div>
      
      <div className="space-y-2">
        <h1 className="text-4xl font-heading font-extrabold tracking-tight text-foreground">
          404 - Page Not Found
        </h1>
        <p className="text-sm text-secondary-foreground max-w-sm mx-auto leading-relaxed">
          The capsule page you are trying to visit does not exist or has been shifted. Check the workspace layout and try again.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Link href="/">
          <Button variant="primary" className="font-semibold text-xs rounded-xl shadow-sm">
            Return to Workspace
          </Button>
        </Link>
      </div>
    </div>
  )
}
