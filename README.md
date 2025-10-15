# Setup Guide

## Prerequisites

1. **Python 3.9+** installed
2. **Node.js 18+** and npm installed
3. **Ollama** installed (for Code Llama)
4. **Git** installed

---

## 🛠️ STEP 1: Setup Backend

### 1.1 Navigate to Backend Folder
```bash
cd backend
```

### 1.2 Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 1.3 Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.4 Create `.env` File
Create `backend/.env` with this content:
```bash
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.com:6543/postgres
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b
CHROMA_PERSIST_DIR=./vectordb
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=10
```

### 1.5 Create Required Folders
```bash
mkdir uploads
mkdir vectordb
```

### 1.6 Initialize Database
```bash
# Run once to create tables
python -c "from backend.db.database import engine; from backend.core.models import Base; Base.metadata.create_all(bind=engine)"
```

---

## 🤖 STEP 2: Setup Ollama

### 2.1 Install Ollama
```bash
# Mac
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

### 2.2 Pull Code Llama Model
```bash
ollama pull codellama:7b
```

### 2.3 Start Ollama Server
```bash
# In a separate terminal, keep this running
ollama serve
```

---

## 🎨 STEP 3: Setup Frontend

### 3.1 Navigate to Frontend Folder
```bash
cd frontend
```

### 3.2 Install Dependencies
```bash
npm install
```



---

## ▶️ STEP 4: Run the Application

### Terminal 1: Backend
```bash
cd backend
# Make sure venv is activated
cd ..
uvicorn backend.main:app --reload
```

### Terminal 2: Ollama
```bash
ollama serve
```

### Terminal 3: Frontend
```bash
cd frontend
npm run dev
```

---


**You're all set! 🎉**
