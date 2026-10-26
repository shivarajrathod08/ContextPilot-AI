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

4. **Three Generation Engines**:
   - ⚡ **Rule-Based Deterministic Engine (Offline / Default)**: Instant, zero-latency generation requiring **no API keys** or network access. Ideal for air-gapped environments, rapid hackathon prototyping, and privacy.
   - 🟢 **Open-Weight Local Model (Ollama)**: Runs an open-weight model on your own machine through Ollama's local HTTP API. No API key, no vendor account, and no additional Python package.
   - 🤖 **AI-Powered Engine (Google Gemini)**: Deep generative synthesis leveraging Google Gemini models (`gemini-2.5-flash` / `gemini-2.0-flash`). Secure key handling with automatic redaction from logs and error messages.

5. **Optional Alan AI Voice Control**:
   - Embeds the Alan AI Web SDK (`@alan-ai/alan-sdk-web`) in the sidebar when `ALAN_PROJECT_KEY` is set.
   - A Studio dialog script sends a `prefillTask` command, and the spoken task is handed to the Python app through a URL query parameter.
   - Stays completely inert when no key is configured.

6. **Interactive Developer Interface**:
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

## 🟢 Mode 3: Open-Weight Local Model (Ollama)

Runs a generative model with open weights on your own hardware. No API key and no data leaves the machine.

1. Install [Ollama](https://ollama.com/download) for your platform.
2. Start the runtime and pull a model:
   ```powershell
   ollama serve
   ollama pull qwen2.5:7b-instruct
   ```
   Any pulled model works; ContextPilot does not assume a specific one. Prefer Apache-2.0 weights (Qwen, Mistral) if licensing matters.
3. Set the runtime location and model, or enter them in the sidebar:
   ```powershell
   $env:OLLAMA_BASE_URL="http://localhost:11434"
   $env:OLLAMA_MODEL="qwen2.5:7b-instruct"
   ```
4. Select **Open-Weight Local Model (Ollama)** in the sidebar and click **Generate**.

The sidebar reports whether Ollama is reachable and whether the model is pulled. If the server is down or the model is missing, ContextPilot explains the fix (`ollama serve` / `ollama pull <model>`) and leaves the deterministic engine available.

> **Deployment note**: `http://localhost:11434` only works when Ollama runs on the same machine as Streamlit. For containers or Streamlit Community Cloud, point `OLLAMA_BASE_URL` at a reachable host — a Cloud app cannot reach your laptop's Ollama.

---

## 🎙️ Optional: Alan AI Voice Control

ContextPilot can take a task by voice using the **Alan AI Web SDK** (Alan AI has no Python SDK; the voice agent runs in the browser). The embed is skipped entirely unless `ALAN_PROJECT_KEY` is set.

1. Create a project in [Alan AI Studio](https://studio.alan.app/register) and copy its key.
2. Add a dialog script that forwards the task to the app:
   ```javascript
   intent('draft a brief for $(TASK)', (p) => {
     play({ command: 'prefillTask', task: p.TASK.value });
   });
   ```
3. Configure and restart the app:
   ```powershell
   $env:ALAN_PROJECT_KEY="your-alan-project-key"
   streamlit run app.py
   ```

The voice agent then fills the task box, and the current engine (rule-based, local, or Gemini) generates the brief. The project key is a public client identifier, not a secret, but it is still read from configuration and never hardcoded.

> **Caveats**: the SDK loads from `studio.alan.app`, so the browser needs network access; microphone capture requires a secure context (localhost or HTTPS); and the voice handoff reloads the page with `?task=...`, so the previously rendered brief is cleared.

---

## 🧪 Running Automated Tests

ContextPilot includes 56 automated tests verifying validation, task-specific generation, stack conflict resolution, repository honesty, API security, the local open-weight engine, the optional Alan AI embed, and Clear/session-state behaviour.

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
- **Open-Weight Engine**: Asserts config resolution, unreachable-server and missing-model messages, 404 handling, and that the default request still uses the rule-based engine.
- **Alan AI Embed**: Asserts the embed stays inert without a key, rejects malformed keys, and loads the SDK only when configured.
- **Clear & Session State**: Asserts Clear resets the task, generated brief, acceptance/QA checkboxes, and error state; that a selected preset cannot resurrect cleared text; and that all three engines stay selectable.

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
│   ├── ai_common.py           # Shared prompt contract, sanitization & brief assembly
│   ├── ai_engine.py           # Gemini API integration with key redaction & fallback
│   ├── openweight_engine.py   # Local open-weight models via Ollama's HTTP API
│   └── alan_voice.py          # Optional Alan AI Web SDK embed & voice handoff
├── tests/
│   ├── __init__.py
│   ├── test_generator.py      # Core engine, validation & security tests
│   ├── test_openweight_engine.py  # Local model config, probing & generation tests
│   ├── test_alan_voice.py     # Alan AI embed configuration tests
│   └── test_app_clear.py      # Clear button & session-state regression tests
├── .env.example               # Template environment configuration
├── .gitignore                 # Python, venv, secrets, and IDE exclusions
├── requirements.txt           # Production dependencies
└── README.md                  # Comprehensive setup and deployment documentation
```

> **Configuration**: ContextPilot reads settings from environment variables. It does not load `.env` automatically, so export the variables in your shell or configure them in your deployment secrets. See `.env.example` for all options.

---

## 🛡️ License

MIT License • Built for the OpenFire Hackathon.
