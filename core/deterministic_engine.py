"""Task-specific deterministic brief generation engine for ContextPilot AI.

Analyzes the user's software task intent, scope, and technical domain (e.g.
Pagination, Authentication Bugs, CRUD Operations, Input Validation, Query Performance,
Payments, Caching, Messaging, UI) to generate precise, component-level architectural
plans and testable checklists. Never falls back to generic user-management templates
for unrelated tasks.
"""

from datetime import datetime
import os
import re
from typing import Dict, List, Optional, Set, Tuple

from core.models import (
    BriefRequest,
    GenerationMode,
    ImplementationBrief,
    ImplementationStep,
    ProjectType,
    TaskScope,
)

# Domain taxonomies
DOMAIN_PAGINATION = "REST_API_PAGINATION"
DOMAIN_AUTH = "AUTH_SECURITY"
DOMAIN_CRUD = "CRUD_OPERATIONS"
DOMAIN_VALIDATION = "INPUT_VALIDATION"
DOMAIN_DB_PERF = "DATABASE_PERFORMANCE"
DOMAIN_PAYMENT = "PAYMENT_BILLING"
DOMAIN_CACHE = "CACHE_RATELIMIT"
DOMAIN_MESSAGING = "MESSAGING_EVENTS"
DOMAIN_FILE = "FILE_STORAGE"
DOMAIN_UI = "UI_FRONTEND"
DOMAIN_GENERAL = "GENERAL"


def detect_technology_stack(text: str) -> Optional[ProjectType]:
    """Detects if explicit technologies are mentioned in the task description.

    Returns the ProjectType if explicitly detected, or None if no technology
    is explicitly stated.
    """
    lowered = text.lower()

    # Java / Spring Boot explicit signals
    java_signals = [
        "spring boot", "spring-boot", "spring framework", "spring data", "spring security",
        "spring", "java", "mockmvc", "jpa", "hibernate", "pom.xml", "pageable", "jparepository",
        "crudrepository", "hikaricp"
    ]
    for sig in java_signals:
        if re.search(r'\b' + re.escape(sig) + r'\b', lowered):
            return ProjectType.JAVA_SPRING

    # Python explicit signals
    python_signals = [
        "python", "fastapi", "flask", "django", "pydantic", "pytest", "testclient",
        "celery", "sqlalchemy", "sqlmodel", "alembic"
    ]
    for sig in python_signals:
        if re.search(r'\b' + re.escape(sig) + r'\b', lowered):
            return ProjectType.PYTHON

    # Web App explicit signals
    web_signals = [
        "react", "next.js", "nextjs", "typescript", "vue", "angular", "node.js",
        "nodejs", "express", "tailwind", "jsx", "tsx"
    ]
    for sig in web_signals:
        if re.search(r'\b' + re.escape(sig) + r'\b', lowered):
            return ProjectType.WEB_APP

    # Mobile explicit signals
    mobile_signals = [
        "flutter", "dart", "react native", "swiftui", "kotlin", "android studio",
        "widgettester", "ios app"
    ]
    for sig in mobile_signals:
        if re.search(r'\b' + re.escape(sig) + r'\b', lowered):
            return ProjectType.MOBILE

    return None


def _clean_user_story_actors(text: str) -> str:
    """Removes framing phrases like 'users should be able to' so 'User' is not

    mistakenly extracted as the domain entity for unrelated tasks.
    """
    cleaned = text
    patterns = [
        r'\bas\s+a\s+user\b',
        r'\b(?:users?|clients?|customers?)\s+(?:should|can|must|will|may)\s+be\s+able\s+to\b',
        r'\b(?:users?|clients?|customers?)\s+(?:should|can|must|will|may|could)\b',
        r'\b(?:allow|allows|let|lets|enable|enables)\s+(?:users?|clients?|customers?)\s+to\b',
        r'\b(?:give|provides?)\s+(?:users?|clients?|customers?)\s+(?:the\s+ability\s+to)?\b',
    ]
    for pat in patterns:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    return cleaned


def _extract_domain(text: str) -> str:
    """Classifies the primary technical domain from task text."""
    lowered = text.lower()

    scores = {
        DOMAIN_PAGINATION: 0,
        DOMAIN_AUTH: 0,
        DOMAIN_DB_PERF: 0,
        DOMAIN_VALIDATION: 0,
        DOMAIN_CRUD: 0,
        DOMAIN_PAYMENT: 0,
        DOMAIN_CACHE: 0,
        DOMAIN_MESSAGING: 0,
        DOMAIN_FILE: 0,
        DOMAIN_UI: 0,
    }

    # Pagination signals
    pag_words = ["pagination", "paginate", "page number", "page size", "pageable", "paging", "limit and offset", "limit/offset"]
    for w in pag_words:
        if w in lowered:
            scores[DOMAIN_PAGINATION] += 3

    # Auth & Security signals
    auth_words = [
        "login", "logout", "auth", "authenticate", "authorization", "jwt",
        "token", "session", "password", "security", "credential", "userdetails",
        "user detail", "encoder", "passwordencoder", "securityconfig", "rbac",
        "permission", "oauth", "sso", "mfa", "2fa", "csrf", "cors"
    ]
    for w in auth_words:
        if w in lowered:
            scores[DOMAIN_AUTH] += 2

    # Database Performance signals
    perf_words = ["query performance", "slow query", "n+1", "optimize query", "database performance", "indexing", "index", "hikaricp"]
    for w in perf_words:
        if w in lowered:
            scores[DOMAIN_DB_PERF] += 3

    # Input Validation signals
    val_words = ["input validation", "bean validation", "validate request", "validation rules", "sanitize input", "validation constraints"]
    for w in val_words:
        if w in lowered:
            scores[DOMAIN_VALIDATION] += 3

    # CRUD signals
    crud_words = ["crud", "create, read, update, delete", "crud api", "crud operations", "create and retrieve", "management api"]
    for w in crud_words:
        if w in lowered:
            scores[DOMAIN_CRUD] += 3

    # Payment signals
    pay_words = ["payment", "stripe", "paypal", "invoice", "billing", "checkout", "subscription", "refund", "charge", "card"]
    for w in pay_words:
        if w in lowered:
            scores[DOMAIN_PAYMENT] += 2

    # Caching & Rate Limiting signals
    cache_words = ["rate limit", "throttling", "token bucket", "redis", "cache", "caching", "memcached", "ttl"]
    for w in cache_words:
        if w in lowered:
            scores[DOMAIN_CACHE] += 2

    # Messaging signals
    msg_words = ["kafka", "rabbitmq", "sqs", "queue", "event", "consumer", "producer", "pubsub", "pub/sub", "celery", "worker"]
    for w in msg_words:
        if w in lowered:
            scores[DOMAIN_MESSAGING] += 2

    # File storage signals
    file_words = ["upload", "s3", "storage", "bucket", "multipart", "blob", "attachment", "export", "csv", "pdf", "download"]
    for w in file_words:
        if w in lowered:
            scores[DOMAIN_FILE] += 2

    # UI signals
    ui_words = ["dark mode", "theme", "component", "modal", "navbar", "responsive", "form", "toggle", "button", "layout", "css"]
    for w in ui_words:
        if w in lowered:
            scores[DOMAIN_UI] += 2

    best_domain = max(scores, key=scores.get)
    if scores[best_domain] > 0:
        return best_domain
    return DOMAIN_GENERAL


def _extract_entity_name(text: str, domain: str) -> str:
    """Extracts a meaningful PascalCase entity name from the user task.

    Avoids mistakenly extracting 'User' for unrelated tasks that use framing
    phrases like 'Users should be able to...'.
    """
    cleaned = _clean_user_story_actors(text)
    lowered = cleaned.lower()

    if domain == DOMAIN_AUTH:
        if "login" in lowered:
            return "Login"
        return "Auth"
    if domain == DOMAIN_UI:
        return "Theme" if ("dark" in lowered or "theme" in lowered) else "View"

    # Specific resource matching patterns
    resource_patterns = [
        r'(?:returns?|lists?|gets?|fetches?|retrieves?)\s+(?:all\s+)?([a-zA-Z]{3,15})s?\b',
        r'pagination\s+(?:to|for)\s+(?:the\s+)?(?:[a-zA-Z\s]+api\s+(?:that\s+)?(?:returns?\s+)?)?([a-zA-Z]{3,15})s?\b',
        r'(?:for|of|managing|manage)\s+(?:all\s+)?([a-zA-Z]{3,15})s?\b',
        r'([a-zA-Z]{3,15})\s+(?:catalog|records?|items?|status|endpoint|api)\b',
    ]
    for pat in resource_patterns:
        match = re.search(pat, cleaned, re.IGNORECASE)
        if match:
            candidate = match.group(1).capitalize()
            ignore = {"all", "the", "rest", "api", "new", "this", "our", "code", "bug", "issue", "task", "feature", "endpoint", "page", "size"}
            if candidate.lower() not in ignore:
                if candidate.endswith("s") and len(candidate) > 4:
                    candidate = candidate[:-1]
                return candidate

    # Prioritize business entities over generic words
    business_entities = [
        ("product", "Product"), ("order", "Order"), ("payment", "Payment"),
        ("invoice", "Invoice"), ("inventory", "Inventory"), ("item", "Item"),
        ("customer", "Customer"), ("notification", "Notification"),
        ("webhook", "Webhook"), ("report", "Report"), ("profile", "Profile"),
        ("account", "Account"), ("cart", "Cart"), ("booking", "Booking"),
        ("subscription", "Subscription"), ("user", "User"),
    ]
    for needle, pascal in business_entities:
        if needle in lowered:
            return pascal

    # Search for candidate nouns following action verbs
    verb_pattern = r"(?:implement|add|fix|create|build|update|refactor|support)\s+(?:a|an|the)?\s*([a-zA-Z]{3,15})"
    match = re.search(verb_pattern, cleaned, re.IGNORECASE)
    if match:
        word = match.group(1).capitalize()
        ignore = {"new", "the", "this", "our", "code", "bug", "issue", "task", "feature", "kafka", "redis", "postgres", "aws", "docker", "pagination", "crud", "validation"}
        if word.lower() not in ignore:
            return word

    return "Feature"


def _derive_title(task: str, scope: TaskScope, domain: str, is_bugfix: bool) -> str:
    """Generates a clean, informative title."""
    first_line = task.strip().split("\n")[0]
    first_line = re.sub(r"^[-*#\d.]+\s*", "", first_line)

    if len(first_line) > 65:
        truncated = first_line[:62].rsplit(" ", 1)[0]
        return f"{truncated}..."
    if first_line:
        return first_line

    prefix = "Fix" if is_bugfix else "Implement"
    domain_label = domain.replace("_", " ").title()
    return f"{prefix} {domain_label} {scope.value}"


def _inspect_repo(repo_path: Optional[str], raw_file_paths: List[str]) -> Tuple[str, bool, List[str], List[str]]:
    """Compares proposed files against a local repository if provided.

    Guarantees honesty: If no repo_path is supplied or it does not exist,
    explicitly labels all files as synthesized recommendations.
    """
    if not repo_path or not repo_path.strip():
        status = "Unconnected / Synthesized (No local repository was scanned)"
        formatted = [f"{f}  [Synthetic Blueprint — Not scanned from disk]" for f in raw_file_paths]
        return status, False, formatted, []

    clean_path = repo_path.strip()
    if not os.path.isdir(clean_path):
        status = f"Unconnected / Path Not Found ('{clean_path}' is not a valid directory)"
        formatted = [f"{f}  [Synthetic Blueprint — Directory not found]" for f in raw_file_paths]
        return status, False, formatted, []

    disk_files: Set[str] = set()
    ignored_dirs = {".git", ".venv", "venv", "node_modules", "target", "build", ".idea", ".vscode", "__pycache__"}

    for root, dirs, files in os.walk(clean_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), clean_path).replace("\\", "/")
            disk_files.add(rel.lower())
            disk_files.add(file.lower())

    formatted_files: List[str] = []
    matched_files: List[str] = []

    for item in raw_file_paths:
        file_path_clean = item.split(" (")[0].strip()
        base_name = os.path.basename(file_path_clean).lower()
        rel_clean = file_path_clean.lower()

        found_match = None
        if rel_clean in disk_files:
            found_match = file_path_clean
        elif base_name in disk_files:
            found_match = base_name

        if found_match:
            formatted_files.append(f"{item}  [✓ Exists in local repository]")
            matched_files.append(found_match)
        else:
            formatted_files.append(f"{item}  [+ Proposed new file]")

    status = f"Connected to local repository at '{clean_path}' ({len(matched_files)} matching files verified on disk)"
    return status, True, formatted_files, matched_files


def generate_deterministic_brief(request: BriefRequest) -> ImplementationBrief:
    """Builds a task-specific, component-accurate implementation brief."""
    domain = _extract_domain(request.task_description)
    entity = _extract_entity_name(request.task_description, domain)
    entity_lower = entity.lower()
    is_bugfix = (
        request.task_scope == TaskScope.BUGFIX
        or any(w in request.task_description.lower() for w in ["bug", "fix", "failing", "broken", "issue", "crash", "error"])
    )
    title = _derive_title(request.task_description, request.task_scope, domain, is_bugfix)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    p_type = request.project_type
    scope = request.task_scope

    raw_files: List[str] = []
    architecture_text = ""
    steps: List[ImplementationStep] = []
    acceptance_criteria: List[str] = []
    testing_checklist: Dict[str, List[str]] = {
        "Unit Tests": [],
        "Integration & API Tests": [],
        "Edge Cases & Resiliency": [],
    }
    pitfalls: List[str] = []

    # =========================================================================
    # 1. Java / Spring Boot Specifics
    # =========================================================================
    if p_type == ProjectType.JAVA_SPRING:
        # 1A. Spring Boot Pagination
        if domain == DOMAIN_PAGINATION:
            raw_files = [
                f"src/main/java/com/app/controller/{entity}Controller.java (REST Controller exposing paginated GET /api/v1/{entity_lower}s)",
                f"src/main/java/com/app/service/{entity}Service.java (Service implementing Pageable query orchestration and DTO mapping)",
                f"src/main/java/com/app/repository/{entity}Repository.java (Spring Data JPA repository extending JpaRepository<{entity}, Long> with Pageable support)",
                f"src/main/java/com/app/dto/{entity}ResponseDto.java (Projection payload representing single {entity_lower} details)",
                f"src/main/java/com/app/dto/PagedResponseDto.java (Generic pagination envelope with content, pageNumber, pageSize, totalElements, totalPages, isLast)",
                f"src/test/java/com/app/controller/{entity}ControllerTest.java (MockMvc integration tests verifying pagination params, boundaries, and metadata)",
            ]
            architecture_text = (
                f"Implement pagination for {entity} using Spring Data's `Pageable` and `Page<T>` abstractions. "
                f"Accept client query parameters (`page`, `size`, optional `sortBy`/`sortDir`), validate boundaries, "
                f"and map database results into a standardized `PagedResponseDto<{entity}ResponseDto>` envelope."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title=f"Extend {entity}Repository with Spring Data Pageable Support",
                    description=f"Configure repository query methods to accept Spring Data Pageable.",
                    target_files=[f"{entity}Repository.java"],
                    key_tasks=[
                        f"Ensure {entity}Repository extends JpaRepository<{entity}, Long>",
                        f"Confirm findAll(Pageable pageable) is available for paginated queries",
                        f"Add indexed sorting support for common sort attributes",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title=f"Build Paginated Service & DTO Response Envelope",
                    description=f"Encapsulate pagination query execution and metadata wrapping.",
                    target_files=[f"{entity}Service.java", "PagedResponseDto.java", f"{entity}ResponseDto.java"],
                    key_tasks=[
                        f"Construct PageRequest.of(page, size, Sort.by(sortBy)) with default fallback values",
                        f"Query repository and map Page<{entity}> elements into {entity}ResponseDto",
                        f"Assemble metadata: pageNumber, pageSize, totalElements, totalPages, isFirst, isLast",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title=f"Expose Paginated REST Endpoint & Query Validation",
                    description=f"Map GET endpoint with default parameters and input constraints.",
                    target_files=[f"{entity}Controller.java"],
                    key_tasks=[
                        f"Map GET /api/v1/{entity_lower}s with @RequestParam(defaultValue = '0') int page and @RequestParam(defaultValue = '20') int size",
                        f"Validate page >= 0 and cap size between 1 and 100 to prevent denial-of-service query spikes",
                        f"Return HTTP 400 Bad Request with descriptive message if negative page or invalid size is passed",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title=f"Author Comprehensive Pagination MockMvc Test Suite",
                    description="Verify pagination contracts, edge cases, and empty datasets.",
                    target_files=[f"{entity}ControllerTest.java"],
                    key_tasks=[
                        f"Test default pagination (page=0, size=20) returns expected slice and metadata",
                        f"Test custom page and size (e.g. page=2, size=5) asserts correct content subset",
                        f"Test invalid parameters (page=-1 or size=0) asserts HTTP 400 Bad Request",
                        f"Test empty repository returns HTTP 200 with totalElements: 0 and content: []",
                    ],
                ),
            ]
            acceptance_criteria = [
                f"Endpoint 'GET /api/v1/{entity_lower}s' accepts 'page' (default: 0) and 'size' (default: 20) query parameters.",
                f"Pagination response wraps items in a structured envelope containing 'content', 'pageNumber', 'pageSize', 'totalElements', and 'totalPages'.",
                "Requests with negative page numbers or size <= 0 return HTTP 400 Bad Request with a clear validation error.",
                "Requests for page numbers exceeding total available pages return HTTP 200 with an empty content list and totalElements: 0.",
                "Database query executes with SQL LIMIT and OFFSET (via Spring Data Pageable) without loading full dataset into memory.",
            ]
            testing_checklist["Unit Tests"] = [
                f"Verify {entity}Service properly constructs PageRequest and maps entity fields to {entity}ResponseDto.",
                "Verify PagedResponseDto correctly calculates totalPages when totalElements is 0 or divisible by pageSize.",
            ]
            testing_checklist["Integration & API Tests"] = [
                f"MockMvc: GET /api/v1/{entity_lower}s without query params defaults to page 0 and size 20.",
                f"MockMvc: GET /api/v1/{entity_lower}s?page=1&size=10 asserts items 11-20 are returned with pageNumber=1.",
                f"MockMvc: GET /api/v1/{entity_lower}s?page=999 returns HTTP 200 with empty content list and totalElements=N.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Invalid parameters: GET with page=-1 or size=-5 returns HTTP 400.",
                "Type mismatch: GET with page=abc returns HTTP 400 with parameter type mismatch error.",
                "Max size cap: GET with size=5000 is automatically capped to max allowed (e.g. 100) or rejected.",
            ]
            pitfalls = [
                "Memory exhaustion: Never use findAll() without Pageable on production datasets.",
                "Zero-indexed vs One-indexed: Document clearly whether 'page' is 0-indexed (Spring standard) or 1-indexed.",
            ]

        # 1B. Spring Boot Authentication & Security
        elif domain == DOMAIN_AUTH:
            raw_files = [
                "src/main/java/com/app/security/SecurityConfig.java (Spring Security filter chain, authentication manager, and permit/authenticated matchers)",
                "src/main/java/com/app/security/CustomUserDetailsService.java (Loads user credentials and authorities from User repository)",
                "src/main/java/com/app/security/PasswordEncoderConfig.java (BCryptPasswordEncoder bean setup and password hashing verification)",
                "src/main/java/com/app/service/AuthenticationService.java (Credential verification, bad credentials handling, and session/token issuance)",
                "src/main/java/com/app/controller/AuthController.java (REST endpoint for /api/v1/auth/login and logout)",
                "src/main/java/com/app/dto/LoginRequestDto.java (Input credentials DTO with @NotBlank username and password validation)",
                "src/main/java/com/app/dto/LoginResponseDto.java (Authentication response payload with token/session details)",
                "src/test/java/com/app/security/SecurityConfigTest.java (Security filter chain and route authorization unit tests)",
                "src/test/java/com/app/service/AuthenticationServiceTest.java (Unit tests for password mismatch, locked user, valid authentication)",
                "src/test/java/com/app/controller/LoginIntegrationTest.java (MockMvc integration tests testing 200 on valid credentials, 401 on bad credentials)",
            ]
            if is_bugfix:
                architecture_text = (
                    "Audit and repair the Spring Security authentication pipeline. Verify SecurityFilterChain "
                    "filter ordering, check PasswordEncoder bean compatibility (e.g. BCrypt hashing mismatch), "
                    "and ensure CustomUserDetailsService handles missing users and disabled accounts gracefully."
                )
                steps = [
                    ImplementationStep(
                        step_number=1,
                        title="Audit SecurityFilterChain & PasswordEncoder Configuration",
                        description="Inspect SecurityConfig filter ordering and verify BCryptPasswordEncoder bean registration.",
                        target_files=["SecurityConfig.java", "PasswordEncoderConfig.java"],
                        key_tasks=[
                            "Verify that SecurityFilterChain declares correct http.authorizeHttpRequests() matching for /auth/login",
                            "Ensure PasswordEncoder bean is injected uniformly into DaoAuthenticationProvider and registration",
                            "Verify CSRF and CORS filters do not prematurely reject preflight OPTIONS or login POST payloads",
                        ],
                    ),
                    ImplementationStep(
                        step_number=2,
                        title="Debug CustomUserDetailsService & Credential Verification",
                        description="Resolve user lookup discrepancies and prevent user enumeration timing attacks.",
                        target_files=["CustomUserDetailsService.java", "AuthenticationService.java"],
                        key_tasks=[
                            "Ensure loadUserByUsername throws UsernameNotFoundException without revealing internal details",
                            "Check account non-expired, credentials non-expired, and enabled boolean flags",
                            "Normalize username/email casing to prevent case-sensitive authentication mismatches",
                        ],
                    ),
                    ImplementationStep(
                        step_number=3,
                        title="Refactor Authentication Controller & Error Responses",
                        description="Map Spring Security authentication exceptions to standard HTTP error envelopes.",
                        target_files=["AuthController.java", "LoginRequestDto.java"],
                        key_tasks=[
                            "Enforce @Valid on LoginRequestDto with descriptive validation messages",
                            "Handle BadCredentialsException and LockedException yielding uniform HTTP 401 response",
                            "Generate secure session or JWT token upon successful authentication",
                        ],
                    ),
                    ImplementationStep(
                        step_number=4,
                        title="Author Authentication Regression & Integration Tests",
                        description="Author MockMvc and unit tests verifying the fix and locking down against regression.",
                        target_files=["AuthenticationServiceTest.java", "LoginIntegrationTest.java"],
                        key_tasks=[
                            "Unit test AuthenticationService with valid credentials, bad passwords, and non-existent users",
                            "MockMvc test /api/v1/auth/login verifying HTTP 200 with token and HTTP 401 on invalid attempt",
                            "Verify brute-force attempt limits and account lock trigger",
                        ],
                    ),
                ]
            else:
                architecture_text = (
                    "Implement standard Spring Security architecture utilizing SecurityFilterChain, DaoAuthenticationProvider, "
                    "and stateless JWT or session-based authentication."
                )
                steps = [
                    ImplementationStep(
                        step_number=1,
                        title="Configure Spring Security & Password Encoding",
                        description="Establish SecurityConfig, register BCryptPasswordEncoder, and configure route permissions.",
                        target_files=["SecurityConfig.java", "PasswordEncoderConfig.java"],
                        key_tasks=[
                            "Define SecurityFilterChain bean with stateless session management or CSRF protection",
                            "Configure DaoAuthenticationProvider with CustomUserDetailsService and PasswordEncoder",
                        ],
                    ),
                    ImplementationStep(
                        step_number=2,
                        title="Implement CustomUserDetailsService & Auth Service",
                        description="Build user retrieval and credential evaluation service.",
                        target_files=["CustomUserDetailsService.java", "AuthenticationService.java"],
                        key_tasks=[
                            "Implement UserDetailsService querying database by email/username",
                            "Build AuthenticationService issuing authenticated credentials and tokens",
                        ],
                    ),
                    ImplementationStep(
                        step_number=3,
                        title="Expose Auth Controller & DTOs",
                        description="Expose REST login and logout routes.",
                        target_files=["AuthController.java", "LoginRequestDto.java"],
                        key_tasks=[
                            "Create @RestController with @PostMapping for /api/v1/auth/login",
                            "Validate input fields using Jakarta Bean Validation",
                        ],
                    ),
                    ImplementationStep(
                        step_number=4,
                        title="Implement Security Unit & MockMvc Tests",
                        description="Verify controller mapping and service authentication logic.",
                        target_files=["AuthenticationServiceTest.java", "LoginIntegrationTest.java"],
                        key_tasks=[
                            "Unit test authentication routines and MockMvc endpoint testing",
                        ],
                    ),
                ]

            testing_checklist["Unit Tests"] = [
                "Verify PasswordEncoder.matches() returns true for matching raw/hashed passwords.",
                "Verify AuthenticationService throws BadCredentialsException on password mismatch.",
                "Verify CustomUserDetailsService throws UsernameNotFoundException when user is absent.",
            ]
            testing_checklist["Integration & API Tests"] = [
                "MockMvc: POST /api/v1/auth/login with valid credentials returns HTTP 200 and auth token.",
                "MockMvc: POST /api/v1/auth/login with invalid password returns HTTP 401 Unauthorized.",
                "Verify protected endpoint rejects requests lacking valid Bearer token with HTTP 401/403.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Prevent timing attack: Ensure verification duration is constant whether username exists or not.",
                "Ensure locked or disabled user accounts cannot authenticate.",
            ]
            pitfalls = [
                "Timing attacks: Do not reveal whether an email exists in error messages; return generic 'Invalid credentials'.",
                "Password storage: Never log raw passwords or store plaintext in memory longer than necessary.",
            ]

        # 1C. Spring Boot Database & Query Performance
        elif domain == DOMAIN_DB_PERF:
            raw_files = [
                f"src/main/java/com/app/repository/{entity}Repository.java (Spring Data JPA repository with @EntityGraph and JOIN FETCH queries)",
                f"src/main/java/com/app/entity/{entity}Entity.java (JPA entity with @Table index definitions for critical filter/sort columns)",
                "src/main/resources/application.yml (HikariCP connection pool configuration and Hibernate statistics logging)",
                f"src/test/java/com/app/performance/{entity}QueryPerformanceTest.java (Integration test verifying single-query execution without N+1)",
            ]
            architecture_text = (
                f"Optimize database access and query performance for {entity}. Eliminate N+1 query patterns using "
                f"`@EntityGraph` or `JOIN FETCH`, establish composite database indexes on high-cardinality filters, "
                f"and tune HikariCP connection pool parameters."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title="Audit Query Execution & Eliminate N+1 Patterns",
                    description=f"Refactor {entity}Repository to fetch related associations eagerly via JOIN FETCH.",
                    target_files=[f"{entity}Repository.java"],
                    key_tasks=[
                        "Identify lazy association iterations triggering secondary SELECT queries",
                        "Apply @EntityGraph(attributePaths = {...}) to entity retrieval methods",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title="Define Strategic Database Indexes",
                    description="Add indexes on frequently filtered and sorted columns.",
                    target_files=[f"{entity}Entity.java"],
                    key_tasks=[
                        "Add @Index annotations on foreign keys and compound query criteria",
                        "Generate Liquibase/Flyway migration applying index concurrently",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title="Tune HikariCP & Hibernate Configuration",
                    description="Configure connection pool sizing and slow query threshold.",
                    target_files=["application.yml"],
                    key_tasks=[
                        "Configure spring.datasource.hikari.maximum-pool-size and connection-timeout",
                        "Enable spring.jpa.properties.hibernate.generate_statistics for performance auditing",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title="Author Query Execution Count Tests",
                    description="Verify that batch operations execute in a deterministic query count.",
                    target_files=[f"{entity}QueryPerformanceTest.java"],
                    key_tasks=[
                        "Assert query execution count <= 2 when fetching collections with associations",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                f"Verify {entity}Repository query constructs proper SQL syntax without syntax errors.",
            ]
            testing_checklist["Integration & API Tests"] = [
                "Assert retrieval of 50 records triggers exactly 1 SELECT query (no N+1).",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Verify database connection pool behavior under simulated concurrent load.",
            ]
            pitfalls = [
                "Cartesian product: Multiple JOIN FETCH clauses on collection associations cause Cartesian explosion; use Set or multiple queries.",
            ]

        # 1D. Spring Boot Input Validation
        elif domain == DOMAIN_VALIDATION:
            raw_files = [
                f"src/main/java/com/app/dto/{entity}RequestDto.java (Input DTO with Jakarta Bean Validation constraints)",
                "src/main/java/com/app/exception/GlobalExceptionHandler.java (@ControllerAdvice handling MethodArgumentNotValidException)",
                f"src/main/java/com/app/controller/{entity}Controller.java (REST Controller enforcing @Valid on incoming request payloads)",
                f"src/test/java/com/app/validation/{entity}ValidationTest.java (MockMvc tests verifying 400 Bad Request on invalid fields)",
            ]
            architecture_text = (
                f"Enforce robust input validation on {entity} endpoints using Jakarta Bean Validation. "
                f"Intercept constraint violations via `@ControllerAdvice` to return standardized RFC 7807 "
                f"Problem Details with field-level error messages."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title=f"Annotate {entity}RequestDto with Validation Constraints",
                    description="Apply declarative validation rules to request fields.",
                    target_files=[f"{entity}RequestDto.java"],
                    key_tasks=[
                        "Add @NotBlank, @Size, @Email, @Min, @Max, or @Pattern constraints",
                        "Provide descriptive, localized message attributes for each constraint",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title="Implement Global Validation Exception Handler",
                    description="Map MethodArgumentNotValidException to structured Problem Details response.",
                    target_files=["GlobalExceptionHandler.java"],
                    key_tasks=[
                        "Extract BindingResult field errors into a Map<String, String>",
                        "Return HTTP 400 Bad Request with timestamp, path, and error map",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title=f"Enforce @Valid in {entity}Controller",
                    description="Ensure incoming request bodies trigger validation before service execution.",
                    target_files=[f"{entity}Controller.java"],
                    key_tasks=[
                        "Annotate @RequestBody parameter with @Valid",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title="Author Comprehensive Validation Test Suite",
                    description="Verify validation failure responses using MockMvc.",
                    target_files=[f"{entity}ValidationTest.java"],
                    key_tasks=[
                        "Test empty body returns 400 with missing required fields",
                        "Test out-of-range values trigger field-specific violation messages",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                "Verify validator flags invalid email formats or out-of-range numbers.",
            ]
            testing_checklist["Integration & API Tests"] = [
                "MockMvc: POST with missing required fields returns HTTP 400 with field errors.",
                "MockMvc: POST with valid payload passes validation and returns HTTP 201/200.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Verify HTML/script tags in string inputs are sanitized or rejected.",
            ]
            pitfalls = [
                "Missing @Valid: Omitting @Valid on controller method causes validation annotations to be silently ignored.",
            ]

        # 1E. Spring Boot Generic / CRUD Operations
        else:
            raw_files = [
                f"src/main/java/com/app/controller/{entity}Controller.java (REST Controller endpoints for {entity_lower})",
                f"src/main/java/com/app/service/{entity}Service.java (Service interface and business logic for {entity_lower})",
                f"src/main/java/com/app/dto/{entity}RequestDto.java (Input DTO with Jakarta validation constraints)",
                f"src/main/java/com/app/dto/{entity}ResponseDto.java (Structured response payload for {entity_lower})",
                f"src/main/java/com/app/repository/{entity}Repository.java (Spring Data JPA repository for {entity_lower})",
                f"src/main/java/com/app/entity/{entity}Entity.java (JPA database entity for {entity_lower})",
                f"src/test/java/com/app/service/{entity}ServiceTest.java (JUnit 5 and Mockito unit tests)",
                f"src/test/java/com/app/controller/{entity}ControllerTest.java (MockMvc integration tests)",
            ]
            architecture_text = (
                f"Implement standard Spring Boot 3 layered architecture for {entity} domain. "
                "Enforce DTO immutability, Jakarta bean validation (@Valid), and clean service layer transactions."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title=f"Create {entity} Entity & JPA Repository",
                    description=f"Model {entity_lower} database table and persistence layer.",
                    target_files=[f"{entity}Entity.java", f"{entity}Repository.java"],
                    key_tasks=[
                        f"Define JPA entity with proper table indexing and auditing fields",
                        f"Create Spring Data JPA repository with required query methods",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title=f"Implement {entity} Service Logic",
                    description=f"Encapsulate core business rules for {entity_lower}.",
                    target_files=[f"{entity}Service.java"],
                    key_tasks=[
                        f"Implement transactional business logic in @Service class",
                        f"Throw domain-specific exceptions on invalid operations",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title=f"Expose {entity} REST Controller & DTOs",
                    description=f"Define HTTP API contracts for {entity_lower}.",
                    target_files=[f"{entity}Controller.java", f"{entity}RequestDto.java"],
                    key_tasks=[
                        f"Declare REST endpoints with appropriate HTTP status codes (POST 201, GET 200, DELETE 204)",
                        f"Add Jakarta bean validation annotations (@NotNull, @Size, @NotBlank)",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title=f"Author {entity} Unit & MockMvc Tests",
                    description=f"Verify controller contracts and service methods.",
                    target_files=[f"{entity}ServiceTest.java", f"{entity}ControllerTest.java"],
                    key_tasks=[
                        f"Unit test {entity}Service with Mockito mocks",
                        f"MockMvc integration test asserting status codes and JSON paths",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                f"Verify {entity}Service logic with valid inputs yields expected result.",
                f"Verify invalid operations throw appropriate domain exceptions.",
            ]
            testing_checklist["Integration & API Tests"] = [
                f"MockMvc: Assert HTTP 200/201 on valid request payload.",
                f"MockMvc: Assert HTTP 400 Bad Request on malformed DTO fields.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Verify database constraint violation produces friendly Problem Details error.",
            ]
            pitfalls = [
                "N+1 Queries: Use JOIN FETCH or EntityGraph on relational entity queries.",
            ]

    # =========================================================================
    # 2. Python Specifics
    # =========================================================================
    elif p_type == ProjectType.PYTHON:
        if domain == DOMAIN_PAGINATION:
            raw_files = [
                f"src/api/{entity_lower}_routes.py (FastAPI route endpoints with page and size Query parameters)",
                f"src/services/{entity_lower}_service.py (Service executing paginated database queries via offset and limit)",
                f"src/models/{entity_lower}_schemas.py (Pydantic models for {entity_lower} items)",
                "src/models/pagination.py (Generic PaginatedResponse[T] schema with items, total, page, size, pages)",
                f"tests/test_{entity_lower}_pagination.py (Pytest integration tests with TestClient verifying pagination)",
            ]
            architecture_text = (
                f"Implement pagination for {entity} using FastAPI query dependencies (`Query(ge=0)`, `Query(gt=0, le=100)`) "
                f"and SQLAlchemy/SQLModel `.offset().limit()` queries. Return a generic `PaginatedResponse[{entity}Schema]`."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title="Define Generic Paginated Response Schema",
                    description="Create reusable generic Pydantic v2 pagination model.",
                    target_files=["src/models/pagination.py"],
                    key_tasks=[
                        "Define PaginatedResponse[T] with items: List[T], total: int, page: int, size: int, pages: int",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title=f"Implement Paginated {entity} Query Service",
                    description="Execute database query using limit and offset.",
                    target_files=[f"src/services/{entity_lower}_service.py"],
                    key_tasks=[
                        "Query total count using func.count() and query slice using offset(page * size).limit(size)",
                        "Package result into PaginatedResponse schema",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title=f"Expose Paginated FastAPI Route",
                    description="Declare endpoint with validated query parameters.",
                    target_files=[f"src/api/{entity_lower}_routes.py"],
                    key_tasks=[
                        "Add page: int = Query(0, ge=0) and size: int = Query(20, gt=0, le=100)",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title=f"Author {entity} Pagination Tests",
                    description="Author TestClient tests verifying pagination slices.",
                    target_files=[f"tests/test_{entity_lower}_pagination.py"],
                    key_tasks=[
                        "Test default page=0 and size=20",
                        "Test negative page returns 422 Unprocessable Entity",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                f"Verify {entity_lower} query calculates correct offset from page and size.",
            ]
            testing_checklist["Integration & API Tests"] = [
                f"TestClient: GET /api/v1/{entity_lower}s returns paginated items and total count.",
                f"TestClient: GET with size=0 or page=-1 returns HTTP 422 Validation Error.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Verify requests exceeding total available records return empty items list with 200 OK.",
            ]
            pitfalls = [
                "Offset performance: For massive tables (millions of rows), consider cursor-based pagination.",
            ]

        elif domain == DOMAIN_AUTH:
            raw_files = [
                "src/core/security.py (Password hashing via Passlib/Bcrypt, JWT encode/decode, token expiration)",
                "src/services/auth_service.py (User credential authentication, password verification, lockout logic)",
                "src/api/auth_routes.py (FastAPI endpoints for /login, /refresh, /logout with OAuth2PasswordBearer)",
                "src/models/auth_schemas.py (Pydantic models for LoginRequest, TokenResponse, UserProfile)",
                "src/core/config.py (JWT secret key, token algorithm, and expiration settings)",
                "tests/test_auth_service.py (Unit tests for password verification, invalid passwords, token expiration)",
                "tests/test_auth_api.py (Integration tests via TestClient for login and protected routes)",
            ]
            architecture_text = (
                "Implement secure authentication following FastAPI best practices. Use Passlib/Bcrypt "
                "for salted password hashing, stateless JWT Bearer tokens, and Pydantic validation schemas."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title="Implement Password Hashing & JWT Security Core",
                    description="Configure cryptographic primitives in security module.",
                    target_files=["src/core/security.py", "src/core/config.py"],
                    key_tasks=[
                        "Implement verify_password and get_password_hash using bcrypt",
                        "Implement create_access_token with exp claim and JWT_SECRET",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title="Build Authentication Service Layer",
                    description="Encapsulate credential validation and user retrieval.",
                    target_files=["src/services/auth_service.py", "src/models/auth_schemas.py"],
                    key_tasks=[
                        "Validate user credentials against stored password hash",
                        "Raise HTTPException(401) with WWW-Authenticate header on bad credentials",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title="Expose Login & Token Endpoints",
                    description="Create FastAPI route handlers for authentication.",
                    target_files=["src/api/auth_routes.py"],
                    key_tasks=[
                        "Implement /login endpoint consuming OAuth2PasswordRequestForm or JSON schema",
                        "Implement current_user dependency extracting and validating Bearer token",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title="Author Authentication Test Suite",
                    description="Author unit and TestClient integration tests.",
                    target_files=["tests/test_auth_service.py", "tests/test_auth_api.py"],
                    key_tasks=[
                        "Test password hashing and verification with pytest",
                        "TestClient integration tests verifying 200 on login and 401 on bad password",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                "Verify bcrypt password verification succeeds on match and fails on mismatch.",
                "Verify expired JWT token throws expired signature exception.",
            ]
            testing_checklist["Integration & API Tests"] = [
                "TestClient: POST /login with valid credentials returns Bearer token.",
                "TestClient: Protected endpoint returns 401 when token is missing or invalid.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Verify constant-time comparison prevents timing attacks.",
            ]
            pitfalls = [
                "Hardcoded secret: Never commit JWT_SECRET to git; load from environment.",
            ]

        elif domain == DOMAIN_CACHE:
            raw_files = [
                "src/core/redis_client.py (Async Redis connection pool and health check)",
                "src/middleware/rate_limiter.py (Token bucket / sliding window rate limiting middleware)",
                "src/core/config.py (Redis connection URL, rate limits, and window settings)",
                "src/api/routes.py (Attach rate limiting dependency to sensitive routes)",
                "tests/test_rate_limiter.py (Unit tests for rate limit counter and sliding window)",
                "tests/test_rate_limit_integration.py (TestClient tests verifying HTTP 429 and Retry-After header)",
            ]
            architecture_text = (
                "Implement distributed rate limiting using Redis and a sliding-window counter. "
                "Intercept requests via FastAPI middleware or endpoint dependencies, returning HTTP 429 when throttled."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title="Configure Redis Client & Pool",
                    description="Set up asynchronous Redis connection management.",
                    target_files=["src/core/redis_client.py", "src/core/config.py"],
                    key_tasks=[
                        "Initialize redis-py async connection pool with retry strategy",
                        "Add graceful fallback if Redis is temporarily unreachable",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title="Build Sliding Window Rate Limiter",
                    description="Implement atomic rate limiting using Redis pipeline or Lua script.",
                    target_files=["src/middleware/rate_limiter.py"],
                    key_tasks=[
                        "Track request timestamps per client IP / API key in Redis sorted set",
                        "Calculate remaining quota and TTL for Retry-After header",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title="Integrate Throttling with API Endpoints",
                    description="Attach rate limiter dependency to target routes.",
                    target_files=["src/api/routes.py"],
                    key_tasks=[
                        "Return HTTP 429 with standard Retry-After and X-RateLimit headers when exceeded",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title="Author Rate Limiting Test Suite",
                    description="Author unit tests with fakeredis and integration tests with TestClient.",
                    target_files=["tests/test_rate_limiter.py", "tests/test_rate_limit_integration.py"],
                    key_tasks=[
                        "Test quota exhaustion returns 429 after threshold",
                        "Verify quota resets after window expiration",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                "Verify Redis sliding window correctly tracks request timestamps.",
                "Verify rate limit calculation produces correct remaining count.",
            ]
            testing_checklist["Integration & API Tests"] = [
                "TestClient: Rapid repeated requests trigger HTTP 429 with Retry-After header.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Graceful degradation: Decide whether to fail-open or fail-closed if Redis is offline.",
            ]
            pitfalls = [
                "Fail-open vs Fail-closed: Explicitly decide behavior if Redis cluster goes down.",
            ]

        else:
            raw_files = [
                f"src/services/{entity_lower}_service.py (Core business logic for {entity_lower})",
                f"src/api/{entity_lower}_routes.py (FastAPI route endpoints for {entity_lower})",
                f"src/models/{entity_lower}_schemas.py (Pydantic validation schemas for {entity_lower})",
                "src/core/config.py (Application configuration and environment variables)",
                f"tests/test_{entity_lower}_service.py (Unit tests with pytest and unittest.mock)",
                f"tests/test_{entity_lower}_api.py (Integration tests with TestClient)",
            ]
            architecture_text = (
                f"Implement clean layered architecture for {entity} in Python. "
                "Enforce strict typing with Pydantic v2 schemas and author comprehensive pytest fixtures."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title=f"Define {entity} Schemas & Config",
                    description=f"Create Pydantic models for {entity_lower}.",
                    target_files=[f"src/models/{entity_lower}_schemas.py", "src/core/config.py"],
                    key_tasks=[
                        f"Define typed request and response Pydantic models",
                        "Add environment settings with sensible defaults",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title=f"Implement {entity} Service Logic",
                    description=f"Build business routines for {entity_lower}.",
                    target_files=[f"src/services/{entity_lower}_service.py"],
                    key_tasks=[
                        f"Implement primary {entity_lower} workflow with error handling",
                        "Add structured logging with contextual metadata",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title=f"Expose {entity} API Routes",
                    description=f"Connect service to FastAPI route handlers.",
                    target_files=[f"src/api/{entity_lower}_routes.py"],
                    key_tasks=[
                        f"Declare route handlers with proper status codes",
                        "Register router in main application",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title=f"Author {entity} Test Suite",
                    description="Write pytest unit and API tests.",
                    target_files=[f"tests/test_{entity_lower}_service.py", f"tests/test_{entity_lower}_api.py"],
                    key_tasks=[
                        f"Author unit tests verifying {entity_lower} edge cases",
                        "Author TestClient integration tests verifying HTTP contract",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                f"Verify {entity_lower} service with valid inputs yields expected result.",
                "Verify boundary conditions trigger Pydantic ValidationError.",
            ]
            testing_checklist["Integration & API Tests"] = [
                "Assert API endpoint returns 200 with expected schema.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Verify handling when dependent external services time out.",
            ]
            pitfalls = [
                "Input sanitization: Validate all fields at the API boundary.",
            ]

    # =========================================================================
    # 3. Web App (React / TypeScript) Specifics
    # =========================================================================
    elif p_type == ProjectType.WEB_APP:
        if domain == DOMAIN_UI:
            raw_files = [
                "src/context/ThemeContext.tsx (React context provider managing light/dark/system theme state)",
                "src/hooks/useTheme.ts (Custom React hook exposing theme state and toggle function)",
                "src/components/ThemeToggle/ThemeToggle.tsx (Accessible button with keyboard shortcuts and ARIA attributes)",
                "src/styles/theme.css (CSS custom properties / design tokens for light and dark palettes)",
                "src/types/theme.ts (TypeScript union types: 'light' | 'dark' | 'system')",
                "src/components/ThemeToggle/__tests__/ThemeToggle.test.tsx (React Testing Library specs for toggle and keyboard interaction)",
            ]
            architecture_text = (
                "Implement a theme provider with React Context, CSS custom properties, and persistent LocalStorage. "
                "Inspect window.matchMedia('(prefers-color-scheme: dark)') on initial render to respect system preferences."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title="Define Theme Types & CSS Variables",
                    description="Establish design tokens for color palettes.",
                    target_files=["src/types/theme.ts", "src/styles/theme.css"],
                    key_tasks=[
                        "Define Theme type ('light' | 'dark' | 'system')",
                        "Declare CSS custom properties on :root and [data-theme='dark']",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title="Build ThemeContext & Storage Hook",
                    description="Manage theme state with LocalStorage persistence.",
                    target_files=["src/context/ThemeContext.tsx", "src/hooks/useTheme.ts"],
                    key_tasks=[
                        "Read saved preference from localStorage; fall back to matchMedia system preference",
                        "Update document.documentElement dataset and localStorage on theme switch",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title="Build Accessible ThemeToggle Component",
                    description="Create toggle UI with keyboard shortcuts.",
                    target_files=["src/components/ThemeToggle/ThemeToggle.tsx"],
                    key_tasks=[
                        "Add aria-label and aria-pressed attributes for screen readers",
                        "Attach global keyboard shortcut (Cmd/Ctrl + J) to toggle theme",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title="Author Component & Storage Tests",
                    description="Test interactions with React Testing Library.",
                    target_files=["src/components/ThemeToggle/__tests__/ThemeToggle.test.tsx"],
                    key_tasks=[
                        "Verify toggle button updates localStorage and document dataset",
                        "Verify component honors system preference when no localStorage key exists",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                "Verify useTheme hook initializes with system preference when localStorage is empty.",
                "Verify toggleTheme switches between light and dark.",
            ]
            testing_checklist["Integration & API Tests"] = [
                "Render ThemeToggle: clicking switches document.documentElement.getAttribute('data-theme').",
                "Verify keyboard shortcut triggers theme toggle.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Handle disabled localStorage in incognito mode gracefully without throwing unhandled exceptions.",
            ]
            pitfalls = [
                "Flash of unstyled theme (FOUT): Add inline script in HTML head to prevent white flash before React hydration.",
            ]

        else:
            raw_files = [
                f"src/features/{entity_lower}/components/{entity}View.tsx (Primary UI component for {entity_lower})",
                f"src/features/{entity_lower}/hooks/use{entity}.ts (Custom React hook managing {entity_lower} state and effects)",
                f"src/features/{entity_lower}/types/{entity_lower}.ts (TypeScript interfaces and state models)",
                f"src/features/{entity_lower}/api/{entity_lower}Api.ts (Client API service for {entity_lower})",
                f"src/features/{entity_lower}/components/__tests__/{entity}View.test.tsx (React Testing Library specs)",
            ]
            architecture_text = (
                f"Implement modular React/TypeScript feature structure for {entity}. "
                "Separate presentational UI from data-fetching and state management using custom hooks."
            )
            steps = [
                ImplementationStep(
                    step_number=1,
                    title=f"Define TypeScript Interfaces for {entity}",
                    description=f"Draft type contracts for {entity_lower}.",
                    target_files=[f"src/features/{entity_lower}/types/{entity_lower}.ts"],
                    key_tasks=[
                        f"Define strict TypeScript types for {entity_lower} data and states",
                    ],
                ),
                ImplementationStep(
                    step_number=2,
                    title=f"Build use{entity} Custom Hook",
                    description=f"Encapsulate state transitions and network requests.",
                    target_files=[f"src/features/{entity_lower}/hooks/use{entity}.ts", f"src/features/{entity_lower}/api/{entity_lower}Api.ts"],
                    key_tasks=[
                        "Implement loading, error, and data states",
                    ],
                ),
                ImplementationStep(
                    step_number=3,
                    title=f"Build {entity}View Presentation Component",
                    description="Create accessible UI elements.",
                    target_files=[f"src/features/{entity_lower}/components/{entity}View.tsx"],
                    key_tasks=[
                        "Ensure responsive layout and ARIA attributes",
                    ],
                ),
                ImplementationStep(
                    step_number=4,
                    title=f"Author {entity} Component Tests",
                    description="Verify rendering and user interactions.",
                    target_files=[f"src/features/{entity_lower}/components/__tests__/{entity}View.test.tsx"],
                    key_tasks=[
                        "Test user interaction and API mocked responses",
                    ],
                ),
            ]
            testing_checklist["Unit Tests"] = [
                f"Verify use{entity} hook handles loading and success states.",
            ]
            testing_checklist["Integration & API Tests"] = [
                f"Verify component renders error banner on API failure.",
            ]
            testing_checklist["Edge Cases & Resiliency"] = [
                "Verify component unmount cancels pending network requests.",
            ]
            pitfalls = [
                "State desynchronization: Use React Query or SWR for remote state caching if appropriate.",
            ]

    # =========================================================================
    # 4. Mobile (Flutter) Specifics
    # =========================================================================
    elif p_type == ProjectType.MOBILE:
        raw_files = [
            f"lib/features/{entity_lower}/presentation/{entity_lower}_screen.dart (Adaptive Flutter screen widget)",
            f"lib/features/{entity_lower}/controllers/{entity_lower}_controller.dart (Riverpod/Bloc state notifier)",
            f"lib/features/{entity_lower}/data/{entity_lower}_repository.dart (Data repository with offline caching)",
            f"lib/features/{entity_lower}/models/{entity_lower}_model.dart (Immutable model with serialization)",
            f"test/features/{entity_lower}/{entity_lower}_controller_test.dart (Unit test for state notifier)",
            f"test/features/{entity_lower}/{entity_lower}_screen_test.dart (Widget tester specs)",
        ]
        architecture_text = (
            f"Implement clean Flutter architecture for {entity}. Use reactive state management "
            "(Riverpod or Bloc), local caching for offline resiliency, and responsive layout widgets."
        )
        steps = [
            ImplementationStep(
                step_number=1,
                title=f"Create {entity} Data Model",
                description=f"Define immutable model with fromJson and toJson.",
                target_files=[f"lib/features/{entity_lower}/models/{entity_lower}_model.dart"],
                key_tasks=["Create model with equality overrides and copyWith"],
            ),
            ImplementationStep(
                step_number=2,
                title=f"Implement Repository & State Controller",
                description=f"Manage state transitions for {entity_lower}.",
                target_files=[f"lib/features/{entity_lower}/data/{entity_lower}_repository.dart", f"lib/features/{entity_lower}/controllers/{entity_lower}_controller.dart"],
                key_tasks=["Coordinate remote REST client and local database cache"],
            ),
            ImplementationStep(
                step_number=3,
                title=f"Build {entity} Presentation Widgets",
                description="Construct adaptive Flutter UI.",
                target_files=[f"lib/features/{entity_lower}/presentation/{entity_lower}_screen.dart"],
                key_tasks=["Ensure tap targets >= 48x48dp and support light/dark themes"],
            ),
            ImplementationStep(
                step_number=4,
                title="Author Widget & Unit Tests",
                description="Verify state controller and widget rendering.",
                target_files=[f"test/features/{entity_lower}/{entity_lower}_controller_test.dart", f"test/features/{entity_lower}/{entity_lower}_screen_test.dart"],
                key_tasks=["Pump widget in WidgetTester and verify state reactions"],
            ),
        ]
        testing_checklist["Unit Tests"] = [
            f"Verify {entity_lower} model serialization and deserialization.",
            "Verify state notifier emits correct state sequence.",
        ]
        testing_checklist["Integration & API Tests"] = [
            "Verify repository offline cache and background sync.",
        ]
        testing_checklist["Edge Cases & Resiliency"] = [
            "Handle device network loss mid-operation.",
        ]
        pitfalls = [
            "Avoid blocking the UI isolate with heavy compute or deserialization.",
        ]

    # =========================================================================
    # 5. General / Other Stacks
    # =========================================================================
    else:
        raw_files = [
            f"src/domain/{entity_lower}_entity (Core domain models and business invariants)",
            f"src/services/{entity_lower}_service (Orchestrator and use-case handlers)",
            f"src/adapters/{entity_lower}_repository (Persistence adapter and database queries)",
            f"src/adapters/http_{entity_lower}_handler (Transport layer / REST API handler)",
            f"tests/unit/test_{entity_lower}_domain (Isolated domain unit tests)",
            f"tests/integration/test_{entity_lower}_pipeline (End-to-end integration tests)",
        ]
        architecture_text = (
            f"Implement Hexagonal / Clean Architecture for {entity}. Keep domain rules isolated "
            "from transport protocols and persistence drivers using dependency inversion."
        )
        steps = [
            ImplementationStep(
                step_number=1,
                title=f"Define {entity} Domain Invariants",
                description="Model core domain entities and validation rules.",
                target_files=[f"src/domain/{entity_lower}_entity"],
                key_tasks=[f"Define {entity} models with business validation rules"],
            ),
            ImplementationStep(
                step_number=2,
                title=f"Implement {entity} Use-Case Handler",
                description="Build application service coordinating business workflows.",
                target_files=[f"src/services/{entity_lower}_service"],
                key_tasks=["Implement workflow with explicit rollback semantics"],
            ),
            ImplementationStep(
                step_number=3,
                title="Implement Infrastructure Adapters",
                description="Fulfill repository and transport interfaces.",
                target_files=[f"src/adapters/{entity_lower}_repository", f"src/adapters/http_{entity_lower}_handler"],
                key_tasks=["Connect to database and expose API endpoints"],
            ),
            ImplementationStep(
                step_number=4,
                title="Author Automated Test Suite",
                description="Author unit and integration tests.",
                target_files=[f"tests/unit/test_{entity_lower}_domain", f"tests/integration/test_{entity_lower}_pipeline"],
                key_tasks=["Verify domain logic and external integration boundaries"],
            ),
        ]
        testing_checklist["Unit Tests"] = [
            f"Verify {entity_lower} domain rules with boundary values.",
        ]
        testing_checklist["Integration & API Tests"] = [
            "Verify adapter integration with test database/service.",
        ]
        testing_checklist["Edge Cases & Resiliency"] = [
            "Ensure system recovers gracefully from unexpected worker process crashes.",
        ]
        pitfalls = [
            "Ensure core domain entities do not take dependencies on external I/O frameworks.",
        ]

    # Inspect repository connection
    repo_status, is_scanned, formatted_file_changes, matched_files = _inspect_repo(
        request.repo_path, raw_files
    )

    if not acceptance_criteria:
        acceptance_criteria = [
            f"The primary capability requested in '{title}' is fully implemented and operational.",
            "All newly introduced configurations and environment variables have safe, documented fallbacks.",
            "Error handling gracefully intercepts malformed inputs and returns clear, actionable error messages.",
            "Automated test coverage passes with 0 failures and no regressions to existing features.",
            "Code adheres to established formatting standards, type safety checks, and project linter rules.",
        ]

    summary = (
        f"**Task Objective**: {request.task_description.strip()}\n\n"
        f"**Domain Focus**: `{domain}` | **Scope**: `{scope.value}` | **Target Stack**: `{p_type.value}`\n\n"
        f"This implementation brief provides an actionable, component-accurate roadmap tailored to "
        f"the {domain.replace('_', ' ').lower()} domain. It specifies exact architecture boundaries, "
        f"file responsibilities, test criteria, and security guardrails."
    )

    return ImplementationBrief(
        title=title,
        summary=summary,
        project_type=p_type,
        task_scope=scope,
        mode_used=GenerationMode.RULE_BASED,
        generated_at=now_str,
        architecture_overview=architecture_text,
        proposed_file_changes=formatted_file_changes,
        implementation_steps=steps,
        acceptance_criteria=acceptance_criteria,
        testing_checklist=testing_checklist,
        security_and_pitfalls=pitfalls,
        repository_status=repo_status,
        is_repo_scanned=is_scanned,
        scanned_matches=matched_files,
    )
