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

  <img width="1920" height="979" alt="image" src="https://github.com/user-attachments/assets/bd52f0e7-31cb-44d6-821e-5304a55199ce" />

## License

This project is licensed under the MIT License.

  

