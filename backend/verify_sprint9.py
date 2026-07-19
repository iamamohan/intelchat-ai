import sys
import os
import asyncio
import sqlite3
import json
import time

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings, document_filter_context
from app.services.conversation_repository import ConversationRepository
from app.services.conversation_service import ConversationService
from app.services.answer_service import AnswerService
from app.services.chroma_service import ChromaService
from app.services.document_service import DocumentService

async def main():
    print("==========================================================")
    print("AI Knowledge Assistant -- Sprint 9 Verification Suite")
    print("==========================================================")

    # First, instantiate ConversationService to trigger DB setup
    print("\nInitializing services and DB schemas...")
    conv_service = ConversationService(settings)
    answer_service = AnswerService(settings)
    chroma_svc = ChromaService(settings)

    # 1. Verify Unified Database Schema
    print("\n--- 1. VERIFYING UNIFIED SQLITE SCHEMA ---")
    db_path = settings.DOCUMENT_REGISTRY_PATH
    if not os.path.isabs(db_path):
        from app.config import BACKEND_DIR
        db_path = os.path.abspath(os.path.join(BACKEND_DIR, db_path))
    
    print(f"Connecting to Unified DB: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    print(f"Existing Tables: {tables}")
    
    required_tables = ["documents", "sessions", "messages", "conversation_summaries", "messages_fts"]
    for t in required_tables:
        if t in tables:
            print(f"  [OK] Table '{t}' exists.")
        else:
            print(f"  [FAIL] Table '{t}' is MISSING!")
            
    # Check FTS5 Virtual Table specifically
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%fts5%';")
    fts_tables = [row["name"] for row in cursor.fetchall()]
    print(f"FTS5 Tables: {fts_tables}")
    if "messages_fts" in fts_tables:
        print("  [OK] FTS5 virtual table 'messages_fts' is verified.")
    else:
        print("  [FAIL] FTS5 table is NOT FTS5 enabled or missing.")
        
    # Check Triggers
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger';")
    triggers = [row["name"] for row in cursor.fetchall()]
    print(f"Triggers: {triggers}")
    required_triggers = ["after_messages_insert", "after_messages_delete", "after_messages_update"]
    for tr in required_triggers:
        if tr in triggers:
            print(f"  [OK] Trigger '{tr}' exists.")
        else:
            print(f"  [FAIL] Trigger '{tr}' is MISSING!")
            
    conn.close()

    # Clean previous test sessions to avoid pollution
    sessions = conv_service.list_sessions()
    for s in sessions:
        if s["title"] in ["Test Session", "Optimized Cloud Computing", "Session B - Edge", "Title Generated Chat"]:
            conv_service.delete_session(s["session_id"])
    print("Cleaned previous verification sessions.")

    # 2. Verify Session Lifecycle & Metadata updates
    print("\n--- 2. VERIFYING SESSION LIFECYCLE & METADATA ---")
    session = conv_service.create_session(title="Test Session", document_filter="doc_123")
    session_id = session["session_id"]
    print(f"Created Session: {session_id} with title: '{session['title']}'")
    
    # Retrieve session details
    retrieved = conv_service.get_session(session_id)
    print(f"Retrieved Session Title: '{retrieved['title']}'")
    print(f"  Metadata -> favorite: {retrieved['favorite']}, pinned: {retrieved['pinned']}, archived: {retrieved['archived']}")
    
    # Update Metadata
    updated = conv_service.update_session_metadata(session_id, {
        "title": "Optimized Cloud Computing",
        "favorite": True,
        "pinned": True,
        "archived": False
    })
    print(f"Updated Session Title: '{updated['title']}'")
    print(f"  Metadata -> favorite: {updated['favorite']}, pinned: {updated['pinned']}, archived: {updated['archived']}")
    
    # List sessions
    sessions = conv_service.list_sessions()
    print("Listing All Sessions:")
    for s in sessions:
        print(f"  - Session ID: {s['session_id']} | Title: '{s['title']}' | Favorite: {s['favorite']} | Pinned: {s['pinned']}")

    # 3. Verify Multi-turn Chat & Query Rewriting
    print("\n--- 3. VERIFYING MULTI-TURN CHAT & QUERY REWRITING ---")
    
    # Create a fresh chat session for title generation
    chat_session = conv_service.create_session()
    chat_sid = chat_session["session_id"]
    print(f"Created new chat session {chat_sid} with default title '{chat_session['title']}'")

    # Mock user questions
    q1 = "What is Cloud Computing?"
    print(f"\nTurn 1 User Question: '{q1}'")
    
    # Check if follow-up (should be False on empty history)
    history = conv_service.repository.get_session_messages(chat_sid, include_summarized=False)
    is_f1 = conv_service.is_follow_up_question(q1)
    print(f"Is follow-up question? {is_f1}")
    
    # Generate answer (Turn 1)
    start_time = time.time()
    resp1 = await answer_service.generate_grounded_answer(q1)
    elapsed1 = time.time() - start_time
    print(f"Assistant Answer (Synchronous pipeline took {elapsed1:.4f}s):")
    print(f"  Answer preview: {resp1.answer[:120]}...")
    print(f"  Citations: {[s.document_name + ' Page ' + str(s.page_number) for s in resp1.sources]}")
    
    # Save user & assistant messages to DB
    import uuid
    user_msg_id = str(uuid.uuid4())
    user_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conv_service.repository.add_message({
        "message_id": user_msg_id,
        "session_id": chat_sid,
        "role": "user",
        "content": q1,
        "timestamp": user_ts,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "response_time": 0.0,
        "is_summarized": False,
        "citations": []
    })
    
    prompt_tokens1 = len(q1) // 4
    completion_tokens1 = len(resp1.answer) // 4
    
    assistant_msg_id = str(uuid.uuid4())
    assistant_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    citations_list1 = [
        {
            "document_name": c.document_name,
            "page_number": c.page_number,
            "chunk_id": c.chunk_id,
            "similarity_score": c.similarity_score
        }
        for c in resp1.sources
    ]
    conv_service.repository.add_message({
        "message_id": assistant_msg_id,
        "session_id": chat_sid,
        "role": "assistant",
        "content": resp1.answer,
        "timestamp": assistant_ts,
        "prompt_tokens": prompt_tokens1,
        "completion_tokens": completion_tokens1,
        "response_time": elapsed1,
        "is_summarized": False,
        "citations": citations_list1
    })
    
    # Trigger Title Generation
    conv_service.handle_title_generation(chat_sid, q1)
    updated_session = conv_service.repository.get_session(chat_sid)
    print(f"Auto-generated Title: '{updated_session['title']}'")
    
    # Turn 2 User Follow-up Question
    q2 = "What are its advantages?"
    print(f"\nTurn 2 User Question: '{q2}'")
    
    # Check if follow-up (should be True)
    is_f2 = conv_service.is_follow_up_question(q2)
    print(f"Is follow-up question? {is_f2}")
    
    # Load history & rewrite query
    history_data = conv_service.load_active_history(chat_sid)
    rewritten_q2 = conv_service.rewrite_user_query(q2, history_data["messages"], history_data["summary"])
    print(f"Rewritten standalone query (for retrieval): '{rewritten_q2}'")
    
    # Generate answer (Turn 2) using rewritten query for context but original question in prompt
    start_time = time.time()
    resp2 = await answer_service.generate_grounded_answer(
        question=q2,
        rewritten_query=rewritten_q2,
        conversation_summary=history_data["summary"],
        recent_messages=history_data["messages"]
    )
    elapsed2 = time.time() - start_time
    print(f"Assistant Answer (Turn 2 took {elapsed2:.4f}s):")
    print(f"  Answer preview: {resp2.answer[:120]}...")
    print(f"  Citations: {[s.document_name + ' Page ' + str(s.page_number) for s in resp2.sources]}")
    
    # Save Turn 2 User & Assistant messages
    user_msg_id2 = str(uuid.uuid4())
    user_ts2 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conv_service.repository.add_message({
        "message_id": user_msg_id2,
        "session_id": chat_sid,
        "role": "user",
        "content": q2,
        "timestamp": user_ts2,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "response_time": 0.0,
        "is_summarized": False,
        "citations": []
    })
    
    prompt_tokens2 = (len(q2) + len(rewritten_q2)) // 4
    completion_tokens2 = len(resp2.answer) // 4
    
    assistant_msg_id2 = str(uuid.uuid4())
    assistant_ts2 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    citations_list2 = [
        {
            "document_name": c.document_name,
            "page_number": c.page_number,
            "chunk_id": c.chunk_id,
            "similarity_score": c.similarity_score
        }
        for c in resp2.sources
    ]
    conv_service.repository.add_message({
        "message_id": assistant_msg_id2,
        "session_id": chat_sid,
        "role": "assistant",
        "content": resp2.answer,
        "timestamp": assistant_ts2,
        "prompt_tokens": prompt_tokens2,
        "completion_tokens": completion_tokens2,
        "response_time": elapsed2,
        "is_summarized": False,
        "citations": citations_list2
    })

    # 4. Verify Full-Text Search (FTS) Match
    print("\n--- 4. VERIFYING FULL-TEXT SEARCH (FTS5) ---")
    fts_results = conv_service.search_chat_history("advantages", chat_sid)
    print(f"FTS Search matches for 'advantages' in Session {chat_sid}:")
    for r in fts_results:
        print(f"  - Message ID: {r['message_id']} | Role: {r['role']} | Content Preview: {repr(r['content'][:80])}...")
    
    fts_all = conv_service.search_chat_history("Cloud")
    print(f"FTS Search matches for 'Cloud' across ALL sessions:")
    for r in fts_all:
        print(f"  - Session ID: {r['session_id']} | Session Title: '{r['session_title']}' | Content: {repr(r['content'][:60])}...")

    # 5. Verify Summarization Trigger & Prompt layout
    print("\n--- 5. VERIFYING SUMMARIZATION TRIGGER & PROMPT ASSEMBLY ---")
    # Temporarily set trigger message count to 2 to force summarization on next turn!
    original_trigger = settings.SUMMARY_TRIGGER_MESSAGES
    settings.SUMMARY_TRIGGER_MESSAGES = 2
    
    print(f"Active unsummarized messages count: {len(conv_service.repository.get_session_messages(chat_sid, include_summarized=False))}")
    print("Triggering summarization check...")
    conv_service.handle_summarization_trigger(chat_sid)
    
    # Reload history & verify summary
    updated_history = conv_service.load_active_history(chat_sid)
    print(f"New Session Summary in SQLite: '{updated_history['summary']}'")
    print(f"Remaining active (unsummarized) messages count: {len(updated_history['messages'])}")
    for m in updated_history['messages']:
        print(f"  - {m['role']}: {repr(m['content'][:40])} (is_summarized={m['is_summarized']})")
        
    # Check full prompt layout
    from app.services.prompt_service import PromptService
    prompt_svc = PromptService()
    # Dummy chunk for prompt building
    from app.models.response_models import RetrievedChunk
    dummy_chunk = RetrievedChunk(
        document_id="doc_test",
        chunk_id=1,
        page_number=1,
        document_name="test.pdf",
        text="Cloud computing is the on-demand availability of computer system resources.",
        character_count=80,
        similarity_score=0.9
    )
    prompt_text, _, _ = prompt_svc.build_grounded_prompt(
        question="What is Edge Computing?",
        chunks=[dummy_chunk],
        conversation_summary=updated_history["summary"],
        recent_messages=updated_history["messages"]
    )
    print("\nAssembled Grounded History-Aware Prompt Layout Preview:")
    print("=" * 60)
    print("\n".join(prompt_text.split("\n")[:18]))  # Print first 18 lines of assembled prompt
    print("...")
    print("=" * 60)
    
    # Restore trigger settings
    settings.SUMMARY_TRIGGER_MESSAGES = original_trigger

    # 6. Verify Token Budget Calculation
    print("\n--- 6. VERIFYING DYNAMIC TOKEN BUDGETING ---")
    budget = conv_service.calculate_token_budget(
        summary=updated_history["summary"],
        history=updated_history["messages"]
    )
    print("Dynamic Token Budget Allocation:")
    for k, v in budget.items():
        print(f"  - {k}: {v}")

    # 7. Verify Session Isolation
    print("\n--- 7. VERIFYING SESSION ISOLATION ---")
    session_b = conv_service.create_session(title="Session B - Edge")
    session_b_id = session_b["session_id"]
    print(f"Created Session B: {session_b_id}")
    
    # Save a message in Session B
    conv_service.repository.add_message({
        "message_id": str(uuid.uuid4()),
        "session_id": session_b_id,
        "role": "user",
        "content": "What is Edge Computing?",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "response_time": 0.0,
        "is_summarized": False,
        "citations": []
    })
    
    # Verify Session A history does not show in Session B
    history_b = conv_service.load_active_history(session_b_id)
    print(f"Session B active messages count: {len(history_b['messages'])}")
    print(f"Session B summary: {history_b['summary']}")
    
    history_a = conv_service.load_active_history(chat_sid)
    print(f"Session A active messages count: {len(history_a['messages'])}")
    print(f"Session A summary: {repr(history_a['summary'][:40]) if history_a['summary'] else 'None'}...")
    
    if len(history_b["messages"]) == 1 and history_b["summary"] is None:
        print("  [OK] Success: Session B is isolated from Session A.")
    else:
        print("  [FAIL] Failure: Leakage detected between sessions!")

    # 8. Verify Quality Metrics & Statistics
    print("\n--- 8. VERIFYING CHAT ANALYTICS & QUALITY METRICS ---")
    metrics = conv_service.get_conversation_quality_metrics()
    print("Compiled Conversation Quality Metrics:")
    for k, v in metrics.items():
        print(f"  - {k}: {v}")

    # 9. Verify Restart Persistence
    print("\n--- 9. VERIFYING RESTART PERSISTENCE ---")
    # Re-instantiate repository to simulate server reboot
    new_repo = ConversationRepository(db_path)
    loaded_session = new_repo.get_session(chat_sid)
    loaded_messages = new_repo.get_session_messages(chat_sid, include_summarized=True)
    print(f"Simulating Server Restart...")
    print(f"Reloaded Session Title: '{loaded_session['title']}'")
    print(f"Reloaded Messages Count: {len(loaded_messages)}")
    if loaded_session["session_id"] == chat_sid and len(loaded_messages) >= 2:
        print("  [OK] Success: Sessions and histories are persistent across server restarts.")
    else:
        print("  [FAIL] Failure: Database persistence failed!")

    print("\n==========================================================")
    print("Sprint 9 Verification Suite Completed successfully!")
    print("==========================================================")

if __name__ == "__main__":
    asyncio.run(main())
