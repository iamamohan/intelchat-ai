import httpx
import asyncio

async def test_session():
    # 1. Create a session
    async with httpx.AsyncClient() as client:
        res = await client.post("http://127.0.0.1:8000/api/chat/session", json={"title": "Ollama Test"})
        if res.status_code != 201:
            print("Failed to create session:", res.text)
            return
        
        session_id = res.json()["session_id"]
        print("Created session:", session_id)
        
        # 2. Send message
        res = await client.post("http://127.0.0.1:8000/api/chat", json={
            "session_id": session_id,
            "question": "Hello",
            "document_id": None
        }, timeout=60.0)
        
        print("Chat response status:", res.status_code)
        print("Chat response body:", res.text)

if __name__ == "__main__":
    asyncio.run(test_session())
