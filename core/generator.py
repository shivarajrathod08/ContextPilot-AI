"""Generator orchestrator for ContextPilot AI.

Coordinates input validation, stack detection & conflict resolution,
deterministic generation, and optional AI model generation.
"""

from typing import List, Tuple
from core.ai_engine import generate_ai_brief, is_ai_available
from core.deterministic_engine import generate_deterministic_brief, detect_technology_stack
from core.models import BriefRequest, GenerationMode, ImplementationBrief, ProjectType


def generate_brief(request: BriefRequest) -> Tuple[ImplementationBrief, List[str]]:
    """Generates an implementation brief according to user preferences and task intent.

    Detects the task's explicit technology stack, resolves conflicts with the
    selected stack, and delegates to the appropriate generation engine.

    Returns:
        (ImplementationBrief, warnings_list)

    Raises:
        ValueError: If input validation fails.
        RuntimeError: If explicit AI mode was requested but failed.
    """
    errors = request.validate()
    if errors:
        raise ValueError("\n".join(errors))

    warnings: List[str] = []

    # 1. Detect explicit stack from task text and resolve conflicts
    detected_stack = detect_technology_stack(request.task_description)
    conflict_warning = None
    effective_request = request

    if detected_stack is not None and detected_stack != request.project_type:
        conflict_warning = (
            f"Detected technology '{detected_stack.value}' in task description, but '{request.project_type.value}' "
            f"was selected. ContextPilot generated the brief for '{detected_stack.value}' to prevent generating an incorrect blueprint."
        )
        warnings.append(conflict_warning)
        # Adapt effective project type so an explicitly stated stack is always honored
        effective_request = BriefRequest(
            task_description=request.task_description,
            project_type=detected_stack,
            task_scope=request.task_scope,
            gemini_api_key=request.gemini_api_key,
            force_ai=request.force_ai,
            repo_path=request.repo_path,
        )

    has_key, key_msg = is_ai_available(request.gemini_api_key)

    if request.force_ai:
        if not has_key:
            raise ValueError(f"AI generation requested, but no valid Gemini API key is configured. ({key_msg})")
        brief = generate_ai_brief(effective_request)
        brief.detected_project_type = detected_stack
        brief.stack_conflict_warning = conflict_warning
        return brief, warnings

    brief = generate_deterministic_brief(effective_request)
    brief.detected_project_type = detected_stack
    brief.stack_conflict_warning = conflict_warning
    return brief, warnings
