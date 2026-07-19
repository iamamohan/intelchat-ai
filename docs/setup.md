# AI Knowledge Assistant Backend - Sprint 1 (FastAPI Foundation)

This is the backend service foundation for the AI Knowledge Assistant, built using Python and FastAPI. It contains modular API routing, automated documentation generation, safe file upload services (handling up to 20MB PDFs), mock chat pipelines, structured logging, and unified JSON error handling.

## Folder Structure

```
backend/
├── app/
│   ├── main.py                  # App initialization, middleware, logging, and error handling
│   ├── config.py                # Environment configuration loading & validation
│   ├── dependencies.py          # Dependency injection utility
│   ├── routes/
│   │   ├── health.py            # Status checkpoint route (GET /)
│   │   ├── upload.py            # File upload endpoints (POST /api/upload)
│   │   └── chat.py              # Assistant query endpoints (POST /api/chat)
│   ├── services/
│   │   └── upload_service.py    # PDF validation, path structure creation, and disk-writing logic
│   ├── models/
│   │   └── response_models.py   # Pydantic schemas for request payloads and standardized JSON responses
│   └── utils/
│       └── file_utils.py        # Safe naming and extension filtering operations
├── uploads/                     # Storage directory created dynamically on successful file upload
├── requirements.txt             # Project library dependencies
├── .env.example                 # Reference template of settings
├── .env                         # Local environment file containing local values
└── README.md                    # Setup and guide documentation (this file)
```

---

## Getting Started

### Prerequisites

Ensure you have Python 3.12+ installed on your system.

### 1. Create a Virtual Environment

Open your terminal, navigate to the `backend/` directory, and run:

```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Environment Configurations

Make a copy of `.env.example` named `.env` and adjust the variables as needed:

```env
APP_NAME="AI Knowledge Assistant"
APP_VERSION="1.0.0"
UPLOAD_FOLDER="uploads"
MAX_UPLOAD_SIZE=20971520
ALLOWED_ORIGINS="http://localhost:3000"
```

*Note: `MAX_UPLOAD_SIZE` is specified in bytes. `20971520` bytes = 20MB.*

### 4. Running the Development Server

Start the application with Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The application will start, and logging output will show configuration settings:
- **API URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Documentation (Redoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Documentation Quick Reference

### GET /
- **Description**: Returns server state check and version.
- **Expected Success Response**:
  ```json
  {
    "status": "running",
    "service": "AI Knowledge Assistant Backend",
    "version": "1.0.0"
  }
  ```

### POST /api/upload
- **Description**: Accepts a multipart form file. The file must be a PDF and under 20MB.
- **Expected Success Response**:
  ```json
  {
    "success": true,
    "filename": "document.pdf",
    "message": "File uploaded successfully"
  }
  ```
- **Error Response Example (Invalid file extension)**:
  ```json
  {
    "success": false,
    "message": "Only PDF files are allowed."
  }
  ```

### POST /api/chat
- **Description**: Accepts JSON questions to trigger a dummy bot reply.
- **Payload**:
  ```json
  {
    "question": "What is AI?"
  }
  ```
- **Expected Response**:
  ```json
  {
    "answer": "Backend connection successful.",
    "citations": []
  }
  ```
