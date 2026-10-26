"""Unit and integration tests for ContextPilot AI core engine.

Verifies:
- Stack detection and conflict resolution (Spring Boot task with Python selected)
- Spring Boot pagination generation (ProductController, Pageable, Page<T>, metadata)
- Task-specific generation (Spring Boot login bug vs order kafka consumer)
- Prevention of generic TaskController / TaskService
- Prevention of generic user-management templates for unrelated tasks with 'Users should...'
- Explicit repository context distinction (synthesized blueprint vs local repository scan)
- Input validation (empty, whitespace, length)
- Gemini API error handling and key redaction
- All 5 project stacks and Markdown formatting
"""

import os
import tempfile
import pytest

from core.models import (
    BriefRequest,
    GenerationMode,
    ImplementationBrief,
    ProjectType,
    TaskScope,
)
from core.generator import generate_brief
from core.deterministic_engine import (
    generate_deterministic_brief,
    detect_technology_stack,
    _clean_user_story_actors,
    _extract_domain,
    _extract_entity_name,
    _derive_title,
    DOMAIN_PAGINATION,
    DOMAIN_AUTH,
    DOMAIN_MESSAGING,
    DOMAIN_PAYMENT,
)
from core.ai_engine import _sanitize_string


class TestValidation:
    """Test validation rules for user input."""

    def test_empty_task_raises_error(self):
        req = BriefRequest(task_description="")
        errors = req.validate()
        assert len(errors) == 1
        assert "cannot be empty" in errors[0]

    def test_whitespace_task_raises_error(self):
        req = BriefRequest(task_description="   \n\t  ")
        errors = req.validate()
        assert len(errors) == 1
        assert "cannot be empty" in errors[0]

    def test_short_task_raises_error(self):
        req = BriefRequest(task_description="Fix bug")
        errors = req.validate()
        assert len(errors) == 1
        assert "too brief" in errors[0]

    def test_valid_task_passes_validation(self):
        req = BriefRequest(
            task_description="Implement Redis caching for user profile endpoints to reduce DB load"
        )
        errors = req.validate()
        assert len(errors) == 0

    def test_generate_brief_raises_value_error_on_invalid_input(self):
        req = BriefRequest(task_description="   ")
        with pytest.raises(ValueError) as excinfo:
            generate_brief(req)
        assert "cannot be empty" in str(excinfo.value)

    def test_invalid_repo_path_detected_in_validation(self):
        req = BriefRequest(
            task_description="Valid software task description here",
            repo_path="C:\\non_existent_folder_path_123456_xyz"
        )
        errors = req.validate()
        assert any("Specified repository path does not exist" in e for e in errors)


class TestStackDetectionAndConflictResolution:
    """Test detection of explicit technologies and conflict handling."""

    def test_spring_boot_task_with_matching_spring_boot_stack(self):
        task = (
            "Add pagination to the Spring Boot REST API that returns all products. "
            "Users should be able to select the page number and page size"
        )
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.JAVA_SPRING,
            task_scope=TaskScope.FEATURE,
        )
        brief, warnings = generate_brief(req)

        assert brief.project_type == ProjectType.JAVA_SPRING
        assert brief.stack_conflict_warning is None
        assert len(warnings) == 0

        file_text = " ".join(brief.proposed_file_changes)
        assert "ProductController.java" in file_text
        assert "ProductService.java" in file_text
        assert "ProductRepository.java" in file_text
        assert "ProductResponseDto.java" in file_text
        assert "ProductControllerTest.java" in file_text

        # Must not generate user-management or generic tasks
        assert "User" not in file_text
        assert "UserDetailsService" not in file_text
        assert "TaskController" not in file_text

        # Content must cover Pageable, Page<T>, page/size params and metadata
        md = brief.to_markdown()
        assert "Pageable" in md
        assert "page" in md.lower()
        assert "size" in md.lower()
        assert "totalElements" in md or "totalPages" in md

    def test_spring_boot_task_with_python_selected_triggers_conflict_resolution(self):
        """Never silently generate a Python plan for an explicitly stated Spring Boot task."""
        task = (
            "Add pagination to the Spring Boot REST API that returns all products. "
            "Users should be able to select the page number and page size"
        )
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.PYTHON,  # Conflict: Python selected for Spring Boot task
            task_scope=TaskScope.FEATURE,
        )
        brief, warnings = generate_brief(req)

        # Must resolve to Java Spring Boot to prevent generating an invalid blueprint
        assert brief.project_type == ProjectType.JAVA_SPRING
        assert brief.stack_conflict_warning is not None
        assert "Detected technology" in brief.stack_conflict_warning
        assert "Python" in brief.stack_conflict_warning
        assert len(warnings) == 1

        file_text = " ".join(brief.proposed_file_changes)
        assert "ProductController.java" in file_text
        assert "ProductRepository.java" in file_text
        assert "src/api" not in file_text  # Should NOT be Python FastAPI files

    def test_python_task_with_fastapi_selected(self):
        task = "Build FastAPI endpoints for searching items with Query validation and Pydantic schemas"
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.PYTHON,
            task_scope=TaskScope.FEATURE,
        )
        brief, warnings = generate_brief(req)

        assert brief.project_type == ProjectType.PYTHON
        assert brief.stack_conflict_warning is None

        file_text = " ".join(brief.proposed_file_changes)
        assert "routes.py" in file_text
        assert "schemas.py" in file_text
        assert "SecurityConfig" not in file_text
        assert "TaskController" not in file_text

    def test_no_technology_mentioned_uses_selected_stack(self):
        task = "Implement input validation on registration DTOs with email and password checks"
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.JAVA_SPRING,
            task_scope=TaskScope.FEATURE,
        )
        brief, warnings = generate_brief(req)

        assert brief.project_type == ProjectType.JAVA_SPRING
        assert brief.stack_conflict_warning is None
        assert len(warnings) == 0


class TestTaskSpecificGeneration:
    """Test task-specific component generation across domains without generic templates."""

    def test_authentication_task_produces_auth_specific_recommendations(self):
        """For a Spring Boot login bug, verify it suggests SecurityConfig, UserDetailsService,

        PasswordEncoder, authentication services, and login tests, and NEVER generic TaskController.
        """
        task = "Fix Spring Boot login bug where users receive HTTP 500 when credentials are validated"
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.JAVA_SPRING,
            task_scope=TaskScope.BUGFIX,
        )
        brief, _ = generate_brief(req)

        file_text = " ".join(brief.proposed_file_changes)

        # Must include relevant authentication components
        assert "SecurityConfig" in file_text
        assert "UserDetailsService" in file_text
        assert "PasswordEncoder" in file_text
        assert "AuthenticationService" in file_text
        assert "Login" in file_text or "Auth" in file_text
        assert "Test" in file_text

        # Must NOT generate generic TaskController or TaskService
        assert "TaskController" not in file_text
        assert "TaskService" not in file_text

    def test_unrelated_tasks_do_not_fall_back_to_user_management_template(self):
        """Phrases like 'Users should be able to view inventory status' must extract

        'Inventory', NOT 'User', and must NOT generate user-management components.
        """
        task = "Users should be able to view inventory status and stock levels"
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.JAVA_SPRING,
            task_scope=TaskScope.FEATURE,
        )
        brief, _ = generate_brief(req)

        file_text = " ".join(brief.proposed_file_changes)
        assert "Inventory" in file_text
        assert "UserDetailsService" not in file_text
        assert "SecurityConfig" not in file_text
        assert "TaskController" not in file_text

    def test_spring_boot_kafka_order_consumer_unrelated_task(self):
        task = "Implement Kafka consumer for order fulfillment events"
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.JAVA_SPRING,
            task_scope=TaskScope.FEATURE,
        )
        brief, _ = generate_brief(req)

        file_text = " ".join(brief.proposed_file_changes)
        assert "Order" in file_text
        assert "SecurityConfig" not in file_text
        assert "PasswordEncoder" not in file_text
        assert "TaskController" not in file_text

    def test_python_rate_limiting_suggests_redis_components(self):
        task = "Add Redis rate limiting to our FastAPI endpoints"
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.PYTHON,
            task_scope=TaskScope.FEATURE,
        )
        brief, _ = generate_brief(req)

        file_text = " ".join(brief.proposed_file_changes)
        assert "redis" in file_text.lower()
        assert "rate_limit" in file_text.lower()
        assert "TaskController" not in file_text

    def test_web_app_dark_mode_suggests_theme_components(self):
        task = "Implement dark mode toggle in React 18 with persistent LocalStorage"
        req = BriefRequest(
            task_description=task,
            project_type=ProjectType.WEB_APP,
            task_scope=TaskScope.FEATURE,
        )
        brief, _ = generate_brief(req)

        file_text = " ".join(brief.proposed_file_changes)
        assert "Theme" in file_text or "theme" in file_text
        assert "useTheme" in file_text or "Toggle" in file_text
        assert "TaskController" not in file_text


class TestRepositoryContextClarity:
    """Ensure explicit distinction between synthesized blueprints and local repositories."""

    def test_unconnected_repository_mode_is_honest_and_explicit(self):
        req = BriefRequest(
            task_description="Build real-time notification service in Python",
            project_type=ProjectType.PYTHON,
            task_scope=TaskScope.FEATURE,
            repo_path=None,
        )
        brief, _ = generate_brief(req)

        assert not brief.is_repo_scanned
        assert "No local repository was scanned" in brief.repository_status

        # Markdown output must explicitly state no repo was scanned
        md = brief.to_markdown()
        assert "ContextPilot did not scan or inspect a local repository" in md
        assert "Synthetic Blueprint" in md

        # File paths must be labeled as synthetic
        assert any("Synthetic Blueprint" in f for f in brief.proposed_file_changes)

    def test_connected_repository_inspects_and_marks_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_repo:
            security_dir = os.path.join(temp_repo, "src", "main", "java", "com", "app", "security")
            os.makedirs(security_dir, exist_ok=True)
            existing_file = os.path.join(security_dir, "SecurityConfig.java")
            with open(existing_file, "w") as f:
                f.write("// Existing Spring Security Config")

            req = BriefRequest(
                task_description="Fix Spring Boot login bug with SecurityConfig and PasswordEncoder",
                project_type=ProjectType.JAVA_SPRING,
                task_scope=TaskScope.BUGFIX,
                repo_path=temp_repo,
            )
            brief, _ = generate_brief(req)

            assert brief.is_repo_scanned
            assert "Connected to local repository" in brief.repository_status
            assert len(brief.scanned_matches) > 0

            # SecurityConfig must be marked as existing in local repo
            matching_lines = [f for f in brief.proposed_file_changes if "SecurityConfig.java" in f]
            assert len(matching_lines) == 1
            assert "Exists in local repository" in matching_lines[0]

            # Newly proposed files must be marked as proposed
            new_lines = [f for f in brief.proposed_file_changes if "PasswordEncoder" in f]
            assert len(new_lines) == 1
            assert "Proposed new file" in new_lines[0]


class TestDeterministicEngineGenerality:
    """Test standard generation across all 5 project types."""

    @pytest.mark.parametrize("project_type", [
        ProjectType.PYTHON,
        ProjectType.JAVA_SPRING,
        ProjectType.WEB_APP,
        ProjectType.MOBILE,
        ProjectType.OTHER,
    ])
    def test_all_project_types_produce_complete_briefs(self, project_type):
        task_text = f"Build secure user profile update module with validation for {project_type.value}"
        req = BriefRequest(
            task_description=task_text,
            project_type=project_type,
            task_scope=TaskScope.FEATURE,
        )
        brief, _ = generate_brief(req)

        assert isinstance(brief, ImplementationBrief)
        assert brief.project_type == project_type
        assert brief.task_scope == TaskScope.FEATURE
        assert brief.mode_used == GenerationMode.RULE_BASED
        assert len(brief.implementation_steps) >= 4
        assert len(brief.acceptance_criteria) >= 4
        assert "Unit Tests" in brief.testing_checklist
        assert "Integration & API Tests" in brief.testing_checklist
        assert "Edge Cases & Resiliency" in brief.testing_checklist
        assert len(brief.proposed_file_changes) > 0


class TestAIEngineFallbackAndSecurity:
    """Test AI Engine handling when keys are missing, invalid, or need redaction."""

    def test_force_ai_without_key_raises_error(self):
        req = BriefRequest(
            task_description="Implement OAuth2 social login with GitHub",
            project_type=ProjectType.WEB_APP,
            task_scope=TaskScope.FEATURE,
            gemini_api_key="",
            force_ai=True,
        )
        with pytest.raises(ValueError) as excinfo:
            generate_brief(req)
        assert "no valid gemini api key is configured" in str(excinfo.value).lower()

    def test_force_ai_with_invalid_key_raises_runtime_error(self):
        req = BriefRequest(
            task_description="Implement OAuth2 social login with GitHub",
            project_type=ProjectType.WEB_APP,
            task_scope=TaskScope.FEATURE,
            gemini_api_key="AIzaSy_FAKE_INVALID_TEST_KEY_12345",
            force_ai=True,
        )
        with pytest.raises(RuntimeError) as excinfo:
            generate_brief(req)
        assert "gemini api invocation failed" in str(excinfo.value).lower()

    def test_api_key_redaction_utility(self):
        fake_key = "AIza" + "Sy" + "0" * 35
        dirty_msg = f"Error communicating with Gemini at https://example.com?key={fake_key}"
        clean_msg = _sanitize_string(dirty_msg, fake_key)
        assert fake_key not in clean_msg
        assert "[REDACTED_API_KEY]" in clean_msg
