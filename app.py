"""ContextPilot AI - Developer Implementation Brief Generator.

A clean, professional developer tool that transforms vague software tasks into
structured, testable implementation briefs with architecture plans, file manifests,
acceptance criteria, and testing checklists.
"""

from datetime import datetime
import os
import re
import streamlit as st

from core.ai_engine import is_ai_available
from core.generator import generate_brief
from core.models import (
    BriefRequest,
    GenerationMode,
    ImplementationBrief,
    ProjectType,
    TaskScope,
)

# Page Configuration
st.set_page_config(
    page_title="ContextPilot AI — Dev Implementation Briefs",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Developer Tool Aesthetic
st.markdown(
    """
    <style>
    .metric-container {
        background-color: rgba(28, 33, 40, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .badge-rule {
        background-color: #1e3a5f;
        color: #60a5fa;
        padding: 5px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        border: 1px solid #3b82f6;
    }
    .badge-ai {
        background-color: #2e1065;
        color: #c084fc;
        padding: 5px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        border: 1px solid #a855f7;
    }
    .badge-repo-synthetic {
        background-color: #3b2a0c;
        color: #fbbf24;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
        border: 1px solid #d97706;
    }
    .badge-repo-scanned {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
        border: 1px solid #059669;
    }
    .file-pill {
        font-family: 'Consolas', 'Menlo', 'Monaco', monospace;
        font-size: 0.88rem;
        padding: 6px 12px;
        border-radius: 6px;
        background: rgba(30, 41, 59, 0.7);
        border-left: 3px solid #3b82f6;
        margin-bottom: 6px;
    }
    .stTextArea textarea {
        font-family: 'Consolas', 'Menlo', 'Monaco', monospace;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Preset sample tasks for quick evaluation
SAMPLE_TASKS = {
    "None": {
        "text": "",
        "project": ProjectType.PYTHON,
        "scope": TaskScope.FEATURE,
    },
    "Spring Boot: REST API Pagination for Products": {
        "text": (
            "Add pagination to the Spring Boot REST API that returns all products. "
            "Users should be able to select the page number and page size"
        ),
        "project": ProjectType.JAVA_SPRING,
        "scope": TaskScope.FEATURE,
    },
    "Spring Boot: Fix Login Authentication Bug (Bugfix)": {
        "text": (
            "Fix Spring Boot login bug where users receive HTTP 500 or bad credentials failure. "
            "Audit SecurityConfig filter chain order, ensure CustomUserDetailsService handles missing users, "
            "verify PasswordEncoder matches BCrypt hashes, and author MockMvc regression tests."
        ),
        "project": ProjectType.JAVA_SPRING,
        "scope": TaskScope.BUGFIX,
    },
    "Python: Redis Rate Limiting on FastAPI Auth": {
        "text": (
            "Add Redis-backed token bucket rate limiting to our FastAPI /login and /register "
            "authentication endpoints. The limit should allow 5 attempts per minute per IP address, "
            "returning HTTP 429 Too Many Requests with a Retry-After header and structured error response."
        ),
        "project": ProjectType.PYTHON,
        "scope": TaskScope.FEATURE,
    },
    "Java / Spring Boot: Idempotent Payment Webhook": {
        "text": (
            "Implement an idempotent Stripe payment webhook consumer in Spring Boot. Verify the webhook "
            "signature against STRIPE_WEBHOOK_SECRET, store event IDs in a PostgreSQL idempotency_keys "
            "table inside a database transaction, and emit an internal application event on successful capture."
        ),
        "project": ProjectType.JAVA_SPRING,
        "scope": TaskScope.FEATURE,
    },
    "Web App: Accessible Dark Mode with LocalStorage": {
        "text": (
            "Implement a dark/light mode toggle in our React 18 / TypeScript application. "
            "It must inspect window.matchMedia('(prefers-color-scheme: dark)') on first visit, persist user "
            "preference in localStorage, support seamless keyboard shortcuts (Cmd/Ctrl + J), and adhere to WCAG AAA contrast."
        ),
        "project": ProjectType.WEB_APP,
        "scope": TaskScope.FEATURE,
    },
    "Mobile / Flutter: Offline-First Notes Synchronization": {
        "text": (
            "Build an offline-first notes feature in Flutter using SQLite / drift. When offline, changes are "
            "queued locally; when internet connectivity resumes, automatically sync records to the backend "
            "REST API with last-write-wins conflict resolution and clear sync progress indicators."
        ),
        "project": ProjectType.MOBILE,
        "scope": TaskScope.FEATURE,
    },
    "Other: S3 Multipart File Upload Worker": {
        "text": (
            "Design a background worker service that accepts chunked multi-gigabyte video uploads, "
            "streams them to Amazon S3 via multipart upload, validates SHA-256 checksums, and publishes "
            "completion events to an Amazon SQS queue."
        ),
        "project": ProjectType.OTHER,
        "scope": TaskScope.FEATURE,
    },
}

# Sidebar Settings
with st.sidebar:
    st.markdown("## ⚙️ Configuration & Stack")
    st.caption("Tailor the execution brief to your target stack and ecosystem.")

    # Preset selection
    st.markdown("### 💡 Quick-Start Presets")
    sample_choice = st.selectbox(
        "Load Example Task",
        options=list(SAMPLE_TASKS.keys()),
        index=0,
        help="Choose a pre-filled real-world task to inspect stack-specific plan generation.",
    )

    preset_project = SAMPLE_TASKS[sample_choice]["project"] if sample_choice != "None" else ProjectType.PYTHON
    preset_scope = SAMPLE_TASKS[sample_choice]["scope"] if sample_choice != "None" else TaskScope.FEATURE

    # Project Type Selector
    project_display_names = ProjectType.get_display_names()
    default_proj_idx = project_display_names.index(preset_project.value) if preset_project.value in project_display_names else 0
    selected_project_display = st.selectbox(
        "Project Type / Stack",
        options=project_display_names,
        index=default_proj_idx,
        help="Select the framework and ecosystem of your target codebase.",
    )
    selected_project_type = ProjectType.from_display_name(selected_project_display)

    # Task Scope Selector
    scope_display_names = TaskScope.get_display_names()
    default_scope_idx = scope_display_names.index(preset_scope.value) if preset_scope.value in scope_display_names else 0
    selected_scope_display = st.selectbox(
        "Task Scope",
        options=scope_display_names,
        index=default_scope_idx,
        help="Classify the development scope (Feature, Bugfix, Refactoring, etc.).",
    )
    selected_scope = TaskScope.from_display_name(selected_scope_display)

    st.markdown("---")
    st.markdown("### 📁 Repository Context")
    repo_path_input = st.text_input(
        "Local Repository Path (Optional)",
        value="",
        placeholder="e.g. C:\\workspace\\my-spring-boot-app",
        help=(
            "If provided and valid, ContextPilot inspects the directory to distinguish files that "
            "already exist on disk from newly proposed files. Leave blank to generate a synthesized blueprint."
        ),
    )
    if repo_path_input.strip():
        if os.path.isdir(repo_path_input.strip()):
            st.markdown('<span class="badge-repo-scanned">🔍 Local Repo Connected</span>', unsafe_allow_html=True)
        else:
            st.caption("⚠️ Directory not found; will default to synthesized blueprint.")
    else:
        st.markdown('<span class="badge-repo-synthetic">⚠️ Synthesized Blueprint (No Repo Scanned)</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🤖 Generation Engine")

    # Engine selection mode
    engine_choice = st.radio(
        "Select Engine Mode",
        options=[
            "Rule-Based Deterministic Engine (Offline / Fast)",
            "AI-Powered Engine (Gemini API)",
        ],
        index=0,
        help=(
            "Rule-Based engine generates task-specific briefs instantly without any network or API keys. "
            "AI-Powered engine calls Google Gemini for generative brief synthesis."
        ),
    )
    use_ai = "AI-Powered" in engine_choice

    user_api_key = ""
    if use_ai:
        env_key_available, _ = is_ai_available()
        default_hint = "GEMINI_API_KEY detected in environment" if env_key_available else "Enter AIzaSy... or set GEMINI_API_KEY"
        user_api_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder=default_hint,
            help="Your key is never logged or displayed. Leave blank to use the GEMINI_API_KEY environment variable.",
        )
        if env_key_available and not user_api_key:
            st.success("✅ `GEMINI_API_KEY` active from environment.")
        elif not env_key_available and not user_api_key:
            st.warning("⚠️ An API key is required for AI mode. Provide one above or switch to Rule-Based engine.")
    else:
        st.info("⚡ **Rule-Based Engine Active**: 100% offline, zero latency, no API keys required.")

    st.markdown("---")
    st.caption("ContextPilot AI • OpenFire Hackathon Edition")

# Main Interface Header
col_header, col_mode = st.columns([3, 1])
with col_header:
    st.title("🧭 ContextPilot AI")
    st.markdown(
        "Transform vague software tickets into **structured, testable implementation briefs** "
        "with architecture plans, file manifests, acceptance criteria, and QA checklists."
    )
with col_mode:
    st.write("")
    if use_ai:
        st.markdown('<div style="text-align:right;"><span class="badge-ai">MODE: GEMINI AI</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:right;"><span class="badge-rule">MODE: DETERMINISTIC</span></div>', unsafe_allow_html=True)

# Determine initial task text
if "task_input" not in st.session_state:
    st.session_state["task_input"] = ""

if sample_choice != "None" and SAMPLE_TASKS[sample_choice]["text"]:
    st.session_state["task_input"] = SAMPLE_TASKS[sample_choice]["text"]

# Text area for software task
st.markdown("### 📝 Enter Software Task / Feature Request")
user_task = st.text_area(
    label="Describe what needs to be implemented or fixed:",
    value=st.session_state["task_input"],
    height=130,
    placeholder=(
        "Example: Fix Spring Boot login bug where users receive HTTP 500. "
        "Audit SecurityConfig filter chain order, verify PasswordEncoder, and add regression tests."
    ),
    help="Be as vague or as detailed as you want. ContextPilot will synthesize architecture and tests.",
    key="current_task_text",
)

col_actions, col_clear, col_space = st.columns([2, 1, 3])
with col_actions:
    generate_clicked = st.button("🚀 Generate Implementation Brief", type="primary", use_container_width=True)
with col_clear:
    if st.button("🧹 Clear", use_container_width=True):
        st.session_state["task_input"] = ""
        st.rerun()

# Generation Logic & Error Handling
if generate_clicked:
    clean_task = (user_task or "").strip()

    # Validation
    if not clean_task:
        st.error("⚠️ **Validation Error**: The software task cannot be empty. Please enter task requirements or pick a sample preset.")
    elif len(clean_task) < 10:
        st.warning("⚠️ **Validation Error**: Please provide at least 10 characters so a meaningful brief can be constructed.")
    else:
        # Build Request
        request = BriefRequest(
            task_description=clean_task,
            project_type=selected_project_type,
            task_scope=selected_scope,
            gemini_api_key=user_api_key.strip() if user_api_key else None,
            force_ai=use_ai,
            repo_path=repo_path_input.strip() if repo_path_input else None,
        )

        spinner_text = "🧠 Synthesizing implementation brief via Gemini AI..." if use_ai else "⚡ Generating task-specific implementation brief via Rule Engine..."
        with st.spinner(spinner_text):
            try:
                brief, warnings = generate_brief(request)
                st.session_state["last_brief"] = brief
                st.session_state["last_warnings"] = warnings
                st.session_state["generation_success"] = True
            except ValueError as val_err:
                st.error(f"⚠️ **Validation Error**: {val_err}")
                st.session_state["generation_success"] = False
            except RuntimeError as run_err:
                st.error(f"❌ **Generation Error**: {run_err}")
                if use_ai:
                    st.info("💡 You can switch to the 'Rule-Based Deterministic Engine' in the sidebar to generate the brief offline without an API key.")
                st.session_state["generation_success"] = False
            except Exception as e:
                st.error(f"❌ **Unexpected Error**: {e}")
                st.session_state["generation_success"] = False

# Render Output if Brief Available
if st.session_state.get("generation_success") and "last_brief" in st.session_state:
    brief: ImplementationBrief = st.session_state["last_brief"]
    markdown_output = brief.to_markdown()

    st.markdown("---")

    if brief.stack_conflict_warning:
        st.warning(f"⚠️ **Stack Conflict**: {brief.stack_conflict_warning}")

    # Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Engine Mode", "Gemini AI" if brief.mode_used == GenerationMode.AI_POWERED else "Deterministic")
    with m2:
        st.metric("Project Stack", brief.project_type.name.replace("_", " "))
    with m3:
        st.metric("Scope", brief.task_scope.name.title())
    with m4:
        repo_metric_label = "Disk Verified" if brief.is_repo_scanned else "Synthesized"
        st.metric("Repo Context", repo_metric_label)

    # Attribution & Transparency Notice
    if brief.mode_used == GenerationMode.AI_POWERED:
        st.info("🤖 **Engine Mode**: Generated dynamically using **Google Gemini AI**.")
    else:
        st.info("⚡ **Engine Mode**: Generated deterministically using ContextPilot's **Rule-Based Engine** (Offline & Instant).")

    if not brief.is_repo_scanned:
        st.caption(
            "⚠️ **Repository Status**: `Unconnected (Synthetic Blueprint)`. "
            "ContextPilot did not inspect a local repository for this brief. File paths are synthesized recommendations based on standard project conventions."
        )
    else:
        st.caption(
            f"🔍 **Repository Status**: `Connected`. Verified against local repository at `{brief.repository_status}`."
        )

    # Tabs for Multiple Views
    tab_rendered, tab_steps, tab_tests, tab_export = st.tabs([
        "📋 Full Implementation Brief",
        "🧩 Step-by-Step Architecture",
        "🧪 Acceptance & QA Checklist",
        "📄 Markdown & Export",
    ])

    with tab_rendered:
        st.markdown(markdown_output)

    with tab_steps:
        st.markdown(f"### Proposed File Manifest for `{brief.project_type.value}`")
        if not brief.is_repo_scanned:
            st.caption("ℹ️ These files are synthesized architectural suggestions based on standard stack conventions.")
        else:
            st.caption(f"ℹ️ Verified against local repository ({len(brief.scanned_matches)} matches found on disk).")

        if brief.proposed_file_changes:
            for file_path in brief.proposed_file_changes:
                st.markdown(f'<div class="file-pill">{file_path}</div>', unsafe_allow_html=True)
        else:
            st.info("See Full Implementation Brief for proposed file layout.")

        st.markdown("### Execution Steps")
        if brief.implementation_steps:
            for step in brief.implementation_steps:
                with st.expander(f"Step {step.step_number}: {step.title}", expanded=True):
                    st.write(step.description)
                    if step.target_files:
                        st.markdown(f"**Target Files:** `{'`, `'.join(step.target_files)}`")
                    if step.key_tasks:
                        st.markdown("**Checklist:**")
                        for t in step.key_tasks:
                            st.checkbox(t, key=f"step_{step.step_number}_{t[:25]}")
        else:
            st.markdown(markdown_output)

    with tab_tests:
        st.markdown("### ✅ Acceptance Criteria")
        if brief.acceptance_criteria:
            for i, ac in enumerate(brief.acceptance_criteria, start=1):
                st.checkbox(f"**[AC-{i}]** {ac}", key=f"ac_check_{i}")
        else:
            st.info("Refer to the Acceptance Criteria section in the Full Implementation Brief.")

        st.markdown("### 🧪 Quality Assurance & Test Matrix")
        if brief.testing_checklist:
            for category, items in brief.testing_checklist.items():
                st.markdown(f"#### {category}")
                for idx, item in enumerate(items):
                    st.checkbox(item, key=f"test_{category}_{idx}")
        else:
            st.info("Refer to testing sections in the Full Brief.")

    with tab_export:
        st.markdown("### Export Implementation Brief")
        st.caption("Save this brief as a standard Markdown file ready to attach to GitHub Issues, Jira tickets, or PR descriptions.")

        clean_title = re.sub(r"[^\w\-_]", "-", brief.title.lower())[:35].strip("-")
        timestamp_slug = datetime.now().strftime("%Y%m%d-%H%M")
        file_name = f"contextpilot-brief-{clean_title or 'task'}-{timestamp_slug}.md"

        col_dl, col_copy = st.columns([1, 2])
        with col_dl:
            st.download_button(
                label="📥 Download as Markdown (.md)",
                data=markdown_output,
                file_name=file_name,
                mime="text/markdown",
                type="primary",
                use_container_width=True,
            )

        st.markdown("#### Markdown Source Code")
        st.code(markdown_output, language="markdown")
