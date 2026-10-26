"""Generator orchestrator for ContextPilot AI.

Coordinates input validation, stack detection & conflict resolution,
deterministic generation, and optional AI model generation.
"""

from dataclasses import replace
from typing import List, Tuple
from core.ai_engine import generate_ai_brief, is_ai_available
from core.deterministic_engine import generate_deterministic_brief, detect_technology_stack
from core.models import BriefRequest, GenerationMode, ImplementationBrief, ProjectType
from core.openweight_engine import generate_local_brief, is_local_llm_available


def generate_brief(request: BriefRequest) -> Tuple[ImplementationBrief, List[str]]:
    """Generates an implementation brief according to user preferences and task intent.

    Detects the task's explicit technology stack, resolves conflicts with the
    selected stack, and delegates to the appropriate generation engine.

    Returns:
        (ImplementationBrief, warnings_list)

    Raises:
        ValueError: If input validation fails or the selected engine is not ready.
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
        effective_request = replace(request, project_type=detected_stack)

    engine = request.resolve_engine()

    if engine == GenerationMode.AI_POWERED:
        has_key, key_msg = is_ai_available(request.gemini_api_key)
        if not has_key:
            raise ValueError(f"AI generation requested, but no valid Gemini API key is configured. ({key_msg})")
        brief = generate_ai_brief(effective_request)
        brief.detected_project_type = detected_stack
        brief.stack_conflict_warning = conflict_warning
        return brief, warnings

    if engine == GenerationMode.LOCAL_OPEN_WEIGHT:
        is_ready, ready_msg = is_local_llm_available(
            effective_request.local_base_url,
            effective_request.local_model,
        )
        if not is_ready:
            raise RuntimeError(f"Open-weight generation requested, but the local model is not ready. ({ready_msg})")
        brief = generate_local_brief(effective_request)
        brief.detected_project_type = detected_stack
        brief.stack_conflict_warning = conflict_warning
        return brief, warnings

    brief = generate_deterministic_brief(effective_request)
    brief.detected_project_type = detected_stack
    brief.stack_conflict_warning = conflict_warning
    return brief, warnings