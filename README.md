# 🧭 ContextPilot AI

> **OpenFire Hackathon Edition**  
> Turn vague software tasks and bug tickets into **structured, testable implementation briefs** with component-level architectural plans, file manifests, acceptance criteria, and QA checklists.

---

## 🌟 Key Highlights & Hackathon Features

1. **Automatic Technology Stack Detection & Conflict Resolution**:
   - Detects explicit technologies mentioned in the prompt (Spring Boot, Java, Python, FastAPI, Django, React, Node.js, Flutter).
   - **Guaranteed Consistency**: If your task explicitly mentions **Spring Boot** but **Python** is selected in the UI, ContextPilot surfaces a clear conflict warning and automatically generates the brief for Spring Boot. **Never silently generates a Python plan for a Spring Boot task!**
   - Falls back smoothly to the selected stack if no technology is explicitly named.

2. **Task-Specific Architecture Generation (No Generic Placeholders)**:
   - For a **Spring Boot REST API pagination request** (*"Add pagination to the Spring Boot REST API that returns all products. Users should be able to select the page number and page size"*):
     - Suggested components: `ProductController.java`, `ProductService.java`, `ProductRepository.java`, `ProductResponseDto.java`, `PagedResponseDto.java`, `ProductControllerTest.java`.
     - Utilizes Spring Data `Pageable` (`PageRequest.of(page, size, Sort.by(...))`) and `Page<Product>`.
     - Covers default query parameters (`page=0, size=20`), max size caps (100), boundary validation (negative page returns HTTP 400), empty datasets (`totalElements: 0`), and response metadata (`pageNumber`, `pageSize`, `totalElements`, `totalPages`, `isFirst`, `isLast`).
     - **Anti-Generic Template Guarantee**: Strips conversational user-story syntax (`Users should be able to...`) so unrelated tasks never fall back to user-management templates!
   - For a **Spring Boot login bug**: Suggests `SecurityConfig.java`, `CustomUserDetailsService.java`, `PasswordEncoderConfig.java`, `AuthenticationService.java`, and MockMvc login tests.
   - Distinct, component-level blueprints for:
     - 🔐 **Authentication Bugs & Security**
     - 📄 **REST API Pagination**
     - 🔄 **CRUD Operations**
     - 🛡️ **Input Validation (Jakarta Bean Validation / Pydantic v2)**
     - ⚡ **Database & Query Performance (N+1 Elimination & Indexing)**
     - 🐍 **Python / FastAPI Features & Middleware**
     - 💳 **Idempotent Payment Webhooks (Stripe)**
     - 📨 **Messaging & Event Consumers (Kafka / RabbitMQ)**
     - 🎨 **Frontend Themes & Dark Mode (React 18 / LocalStorage)**

3. **Transparent Repository Context**:
   - **Guaranteed Honesty**: ContextPilot explicitly marks when file paths are **Synthesized Blueprints** rather than claiming to have scanned a local repository.
   - **Optional Local Repo Inspection**: Supply your local project path (e.g., `C:\workspace\my-app`) to compare proposed architecture against existing files on disk, clearly distinguishing existing components from newly proposed files.

4. **Dual Generation Engines**:
   - ⚡ **Rule-Based Deterministic Engine (Offline / Default)**: Instant, zero-latency generation requiring **no API keys** or network access. Ideal for air-gapped environments, rapid hackathon prototyping, and privacy.
   - 🤖 **AI-Powered Engine (Google Gemini)**: Deep generative synthesis leveraging Google Gemini models (`gemini-2.5-flash` / `gemini-2.0-flash`). Secure key handling with automatic redaction from logs and error messages.

5. **Interactive Developer Interface**:
   - Sleek dark-mode aesthetic with monospace typography.
   - Preset task selector for quick evaluation across Python, Java/Spring Boot, React, and Flutter.
   - Interactive checklist trackers for execution steps and acceptance criteria (`[AC-1]`, `[AC-2]`).
   - One-click `.md` export with clean timestamps and slugs ready for GitHub Issues or Jira tickets.

---

## 🚀 Getting Started on Windows

### Prerequisites
- Python 3.10+ installed (`python --version`)

### 1. Open the Project
Open PowerShell or Command Prompt in the project folder:
```powershell
cd "c:\Users\Rathlavath\Downloads\Alan AI\ContextPilot"
```

### 2. Activate Virtual Environment
A dedicated virtual environment `.venv` is included:

**In PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell blocks script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

**In Command Prompt (cmd.exe):**
```cmd
.\.venv\Scripts\activate.bat
```

*(Optional: To create a fresh environment from scratch: `python -m venv .venv` and `pip install -r requirements.txt`)*

### 3. Launch the Application
```powershell
streamlit run app.py
```
Or run directly via the virtual environment executable:
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

The app will launch at:
👉 **`http://localhost:8501`**

---

## ⚡ Mode 1: Offline Deterministic Mode (Default)

ContextPilot requires **no setup, no API keys, and no internet connectivity** to generate complete implementation briefs.

1. Launch `streamlit run app.py`.
2. In the sidebar, leave the engine set to **Rule-Based Deterministic Engine (Offline / Fast)**.
3. Choose a preset or type your software task (e.g., *"Add pagination to the Spring Boot REST API that returns all products"*).
4. Click **🚀 Generate Implementation Brief**.
5. Your brief is synthesized in milliseconds!

---

## 🤖 Mode 2: AI-Powered Mode (Google Gemini)

To unlock deep generative synthesis using Google's Gemini models:

1. Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).
2. You can configure the key in either of two ways:
   - **Environment Variable (Recommended for CLI / CI):**
     ```powershell
     # In PowerShell
     $env:GEMINI_API_KEY="AIzaSyYourActualKeyHere"

     # In Command Prompt (cmd)
     set GEMINI_API_KEY=AIzaSyYourActualKeyHere
     ```
   - **Sidebar Setting (Session Only):**
     Toggle **Engine Mode** to `AI-Powered Engine (Gemini API)` and enter your key in the password field. Keys are kept strictly in-memory and are **never logged, persisted, or exposed in UI error messages**.
3. If an invalid key is provided or the API is unreachable, ContextPilot displays a clear error explanation and offers a one-click fallback to the offline engine.

---

## 📁 Repository Context Modes

ContextPilot explicitly reports the provenance of all proposed file paths:

- **Synthesized Blueprint (Default)**:
  When no local repository is specified, ContextPilot clearly indicates:
  `⚠️ Repository Status: Unconnected (Synthetic Blueprint — No local repository was scanned)`
  File recommendations are derived from standard architectural patterns for the selected stack.
- **Local Repository Inspection (Optional)**:
  Enter your local project path in the sidebar (e.g., `C:\workspace\my-spring-boot-app`). ContextPilot scans your workspace on disk and categorizes files:
  - `[✓ Exists in local repository]` (Existing component to be modified)
  - `[+ Proposed new file]` (New component to be created)

---

## 🧪 Running Automated Tests

ContextPilot includes 25 automated tests verifying validation, task-specific generation, stack conflict resolution, repository honesty, and API security.

Run the test suite with pytest:
```powershell
.\.venv\Scripts\pytest.exe -v
```

### What the Tests Cover:
- **Spring Boot Pagination**: Asserts `ProductController.java`, `ProductService.java`, `ProductRepository.java`, `Pageable`, `Page<T>`, metadata, and no user-management pollution.
- **Stack Conflict Resolution**: Verifies that selecting Python for a Spring Boot task emits a clear warning and generates a Spring Boot blueprint.
- **FastAPI / Python Tasks**: Verifies FastAPI routes, Pydantic schemas, and TestClient tests.
- **Task Specificity**: Verifies that a Spring Boot login bug recommends `SecurityConfig`, `UserDetailsService`, and `PasswordEncoder`.
- **Anti-Generic User Template**: Verifies that phrases like *"Users should be able to view inventory status"* extract `Inventory` instead of `User`.
- **Validation**: Verifies rejection of empty, whitespace-only, and excessively short tasks.
- **Honesty & Provenance**: Asserts that unconnected briefs explicitly declare no repository was scanned.
- **Connected Inspection**: Asserts that files found on disk are properly tagged with `[✓ Exists in local repository]`.
- **Security & Redaction**: Asserts that API keys are stripped from error strings and never leaked.

---

## 🚢 Deployment Guide

### Option 1: Streamlit Community Cloud
1. Push this repository to GitHub.
2. Sign in to [share.streamlit.io](https://share.streamlit.io).
3. Connect your repository, set main file path to `app.py`.
4. (Optional) In Advanced Settings, add `GEMINI_API_KEY` under Secrets.

### Option 2: Docker / Container Deployment
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t contextpilot-ai .
docker run -p 8501:8501 -e GEMINI_API_KEY="your-key" contextpilot-ai
```

---

## 📂 Project Architecture

```text
ContextPilot/
├── app.py                     # Streamlit web application & developer dashboard
├── core/
│   ├── __init__.py
│   ├── models.py              # BriefRequest, ImplementationBrief, enums & Markdown renderer
│   ├── generator.py           # Engine orchestrator, stack detector, & conflict resolver
│   ├── deterministic_engine.py# Task-specific domain classifier and repo inspector
│   └── ai_engine.py           # Gemini API integration with key redaction & fallback
├── tests/
│   ├── __init__.py
│   └── test_generator.py      # Comprehensive pytest test suite (25 tests)
├── .env.example               # Template environment configuration
├── .gitignore                 # Python, venv, secrets, and IDE exclusions
├── requirements.txt           # Production dependencies
└── README.md                  # Comprehensive setup and deployment documentation
```

---

## 🛡️ License

MIT License • Built for the OpenFire Hackathon.
