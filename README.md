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

## Demo

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/19d101e2-58cf-41ac-b1fa-99268e5235c5" />

  A live demo is currently unavailable because the backend is not deployed yet. You can run the project locally by following the installation instructions        provided   in this repository.

### Run Locally

#### 1. Clone the repository

```bash
git clone https://github.com/iamamohan/intelchat-ai.git
cd intelchat-ai
```

#### 2. Backend Setup

```bash
cd backend

python -m venv venv
```

Activate the virtual environment:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory and configure the required environment variables.

Start the backend server:

```bash
uvicorn app.main:app --reload
```

The backend will be available at:

```
http://127.0.0.1:8000
```

#### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend

npm install

npm run dev
```

The frontend will be available at:

```
http://localhost:3000
```

#### 4. Start Ollama

Make sure Ollama is installed and running.

Pull the required model (if not already installed):

```bash
ollama pull qwen2.5:3b
```

Start the model:

```bash
ollama run qwen2.5:3b
```

#### 5. Use the Application

- Open **http://localhost:3000**
- Upload a PDF document.
- Ask questions about the uploaded document.
- The AI will retrieve relevant information and generate context-aware responses.

## Author

**Mohan Kumar**

- GitHub: https://github.com/iamamohan
- LinkedIn: https://www.linkedin.com/in/mohan-kumar-sa
- Portfol: https://amohanverse.netlify.app/



  

