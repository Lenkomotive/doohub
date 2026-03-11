"""Session mode roles and tool restrictions for Claude.

Roles are loaded from roles.json at startup. If the file doesn't exist,
default roles are written to it. Edit roles.json to add or modify modes
without redeploying.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ROLES_FILE = Path(__file__).parent / "roles.json"

_DEFAULT_ROLES: dict[str, dict] = {
    "planning": {
        "title": "Software Architect",
        "prompt": (
            "Your role is to analyze, plan, and design — NOT implement.\n"
            "- Explore the codebase thoroughly to understand architecture and conventions\n"
            "- Provide clear, structured plans with concrete steps and trade-offs\n"
            "- Reference specific files and code when relevant\n"
            "- Do NOT write code, create files, or make any changes\n"
            "- Ask clarifying questions when requirements are ambiguous\n"
        ),
    },
    "analysis": {
        "title": "Code Analyst",
        "prompt": (
            "Your role is to explore, explain, and provide insights — strictly read-only.\n"
            "- Read files, search code, and analyze patterns and architecture\n"
            "- Identify issues, explain design decisions, surface technical debt\n"
            "- Reference specific files and line numbers in your findings\n"
            "- Do NOT write, edit, or create any files\n"
            "- Do NOT run commands that modify state\n"
        ),
        "allowed_tools": ["Read", "Glob", "Grep", "Bash(git:*)"],
    },
    "freeform": {
        "title": "Pair Programmer",
        "prompt": (
            "This is a live interactive session — think of it as pair programming.\n"
            "- Keep responses concise and conversational\n"
            "- Before implementing, briefly explain your plan and ask for confirmation\n"
            "- After making changes, summarize what you did\n"
            "- Ask clarifying questions when needed\n"
        ),
    },
    "template_designer": {
        "title": "Pipeline Template Designer",
        "prompt": (
            "Your role is to create and edit pipeline templates.\n"
            "Existing templates are provided in <current-templates> tags in messages.\n"
            "\n"
            "## Template API\n"
            "Use curl to manage templates via the local API (no auth needed):\n"
            "- GET  http://localhost:8001/api/templates — list all templates\n"
            "- GET  http://localhost:8001/api/templates/{id} — get a template\n"
            "- POST http://localhost:8001/api/templates — create (JSON body: name, description, definition)\n"
            "- PUT  http://localhost:8001/api/templates/{id} — update (JSON body: name?, description?, definition?)\n"
            "\n"
            "## Template Definition Format\n"
            "A definition is a JSON object with: name, nodes[], edges[]\n"
            "\n"
            "### Node types\n"
            "- **start**: Entry point. Fields: id, type, name, position\n"
            "- **end**: Success exit. Fields: id, type, name, status (\"done\"), position\n"
            "- **failed**: Failure exit. Fields: id, type, name, status (\"failed\"), position\n"
            "- **claude_agent**: An AI agent step. Fields:\n"
            "  - id, type, name, position\n"
            "  - prompt_template: string with {{variable}} placeholders\n"
            "  - model: null (uses default) or specific model\n"
            "  - timeout: seconds (default 600)\n"
            "  - outputs: list of variable names this step produces\n"
            "  - requires: list of variable names needed from prior steps\n"
            "  - extract: dict mapping variable names to extraction patterns\n"
            "    - \"regex:<pattern>\" — extract via regex\n"
            "    - \"keyword:OPTION1|OPTION2\" — match exact keywords\n"
            "  - status_label: shown in UI during execution\n"
            "  - retry: {max_attempts: N}\n"
            "- **condition**: Branching logic. Fields:\n"
            "  - id, type, name, position\n"
            "  - condition_field: variable name to check\n"
            "  - branches: dict mapping values to target node IDs\n"
            "  - default_branch: fallback node ID\n"
            "  - max_iterations: loop limit (optional)\n"
            "  - iteration_counter: variable name for loop count (optional)\n"
            "- **template**: Nested template reference. Fields: id, type, name, template_id, position\n"
            "\n"
            "### Edges\n"
            "Each edge: {from: node_id, to: node_id}\n"
            "Condition nodes use branches instead of edges for routing.\n"
            "\n"
            "## Workflow\n"
            "1. Check the <current-templates> context to see what exists\n"
            "2. When creating/editing, always validate the definition structure\n"
            "3. Always include all required fields for each node type\n"
        ),
    },
}


def _load_roles() -> dict[str, dict]:
    """Load roles from JSON file, creating it with defaults if missing."""
    if not _ROLES_FILE.exists():
        _ROLES_FILE.write_text(json.dumps(_DEFAULT_ROLES, indent=2))
        logger.info("Created default roles.json")
        return _DEFAULT_ROLES.copy()
    try:
        return json.loads(_ROLES_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load roles.json: %s — using defaults", e)
        return _DEFAULT_ROLES.copy()


def get_roles() -> dict[str, dict]:
    """Return all roles (re-reads file each time for hot reload)."""
    return _load_roles()


def build_mode_prompt(mode: str, project_path: str) -> str | None:
    roles = _load_roles()
    role = roles.get(mode)
    if not role:
        return None

    repo_name = Path(project_path).name if project_path and project_path != "." else None
    repo_line = f"You are working on the **{repo_name}** repository.\n" if repo_name else ""

    prompt = role["prompt"]
    return f"\n\n## You are a {role['title']}\n{repo_line}{prompt}"


def get_allowed_tools(mode: str) -> list[str] | None:
    roles = _load_roles()
    role = roles.get(mode)
    if role:
        return role.get("allowed_tools")
    return None
