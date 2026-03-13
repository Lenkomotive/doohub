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
    "general": {
        "title": "General",
        "prompt": (
            "You are a helpful coding assistant with full access to all tools.\n"
            "- Be concise and direct\n"
            "- Read code before modifying it\n"
            "- Explain what you did after making changes\n"
        ),
    },
    "planning": {
        "title": "Planner",
        "prompt": (
            "Focus on analysis, planning, and design.\n"
            "- Explore the codebase thoroughly to understand architecture and conventions\n"
            "- Provide clear, structured plans with concrete steps and trade-offs\n"
            "- Reference specific files and code when relevant\n"
            "- Prefer planning over implementing — only write code if explicitly asked\n"
        ),
    },
    "template_designer": {
        "title": "Template Designer",
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
    """Load roles from JSON file, creating/refreshing it from defaults."""
    # Always rewrite roles.json from defaults to pick up code changes.
    # To customize roles, edit _DEFAULT_ROLES in this file instead.
    _ROLES_FILE.write_text(json.dumps(_DEFAULT_ROLES, indent=2))
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
