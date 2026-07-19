# IntelChat - AI Knowledge Assistant

IntelChat is an AI-powered Retrieval-Augmented Generation (RAG) application that allows users to upload PDF documents and ask questions using a local Large Language Model (LLM). It combines semantic search with AI to provide accurate, context-aware responses from uploaded documents.

## Features

- Upload and chat with PDF documents
- AI-powered question answering
- Retrieval-Augmented Generation (RAG)
- Semantic search using ChromaDB
- Streaming AI responses
- Conversation history
- Pinned conversations
- Modern and responsive UI
- Local AI inference using Ollama

## Tech Stack

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend
- FastAPI
- Python

### AI & Database
- Ollama
- Qwen 2.5
- ChromaDB
- Sentence Transformers
- SQLite

## Project Structure

```
IntelChat-AI/
├── backend/
├── frontend/
├── docs/
└── README.md
```

## How It Works

1. Upload a PDF document.
2. The document is processed and converted into embeddings.
3. Embeddings are stored in ChromaDB.
4. Ask questions about the uploaded document.
5. Relevant content is retrieved and sent to the LLM.
6. IntelChat generates an accurate response based on the document.

## Future Enhancements

- Multi-document support
- OCR for scanned PDFs
- User authentication
- Cloud deployment
- Voice interaction

## Author

Mohan Kumar A

- GitHub: https://github.com/iamamohan
- LinkedIn: linkedin.com/in/mohan-kumar-sa

  <img width="1920" height="979" alt="image" src="https://github.com/user-attachments/assets/bd52f0e7-31cb-44d6-821e-5304a55199ce" />



This project is licensed under the MIT License.
