"use client"

import * as React from "react"
import { useSearchParams } from "next/navigation"
import { useSessionStore } from "@/store/useSessionStore"
import { ChatContainer } from "@/features/chat/components/ChatContainer"

function SessionSync() {
  const searchParams = useSearchParams()
  const sessionId = searchParams.get("session")
  const { setActiveSessionId, activeSessionId } = useSessionStore()

  React.useEffect(() => {
    if (sessionId && sessionId !== activeSessionId) {
      setActiveSessionId(sessionId)
    }
  }, [sessionId, activeSessionId, setActiveSessionId])

  return null
}

export default function Home() {
  return (
    <>
      <React.Suspense fallback={null}>
        <SessionSync />
      </React.Suspense>
      <ChatContainer />
    </>
  )
}
