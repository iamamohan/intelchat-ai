# IntelChat

IntelChat is an AI-powered RAG (Retrieval-Augmented Generation) application that lets users upload PDF documents and ask questions using a local Large Language Model (LLM). It retrieves relevant information from documents and generates accurate, context-aware answers.

## Features

- Upload and chat with PDF files
- AI-powered question answering
- Retrieval-Augmented Generation (RAG)
- Semantic search with ChromaDB
- Streaming responses
- Conversation history
- Responsive user interface
- Local AI using Ollama

## Tech Stack

**Frontend**
- Next.js
- React
- TypeScript
- Tailwind CSS

**Backend**
- FastAPI
- Python

**AI & Database**
- Ollama
- Qwen 2.5
- ChromaDB
- Sentence Transformers
- SQLite

## Project Structure

```text
IntelChat/
├── backend/
├── frontend/
├── docs/
└── README.md
```

## Workflow

1. Upload a PDF document.
2. The document is processed and converted into embeddings.
3. Embeddings are stored in ChromaDB.
4. Ask questions about the document.
5. Relevant content is retrieved.
6. The AI generates an answer based on the retrieved context.

## Future Improvements

- Support multiple documents
- OCR for scanned PDFs
- User authentication
- Cloud deployment
- Voice support

## Author

**Mohan Kumar**

- GitHub: https://github.com/iamamohan
- LinkedIn: https://www.linkedin.com/in/mohan-kumar-sa
- Portfol: https://amohanverse.netlify.app/

  <img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/19d101e2-58cf-41ac-b1fa-99268e5235c5" />


## License

This project is licensed under the MIT License.

  

