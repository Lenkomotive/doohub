"""Add Flutter Dependency Updater pipeline template

Revision ID: 013
Revises: 012
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"

TEMPLATE_NAME = "Flutter Dependency Updater"
TEMPLATE_DESC = (
    "Audit and update all Flutter dependencies to latest major versions, "
    "one by one. Fixes or reverts broken updates, creates PR with report."
)
TEMPLATE_DEF = {
    "name": "Flutter Dependency Updater",
    "nodes": [
        {
            "id": "start",
            "type": "start",
            "name": "Start",
            "position": {"x": 0, "y": 0},
        },
        {
            "id": "audit",
            "type": "claude_agent",
            "name": "Audit Dependencies",
            "prompt_template": (
                "You are auditing Flutter dependencies for major version updates.\n"
                "The repo is already pulled and on a fresh state.\n\n"
                "Steps:\n"
                "1. Create a new branch: `chore/update-flutter-deps`\n"
                "2. Navigate to the Flutter project directory (look for pubspec.yaml)\n"
                "3. Run `flutter pub outdated` to see all outdated dependencies\n"
                "4. Identify all dependencies that have a newer MAJOR version available (resolvable column)\n"
                "5. List them clearly\n\n"
                "Output your findings as a structured list. For each outdated dependency, include:\n"
                "- Package name\n"
                "- Current version\n"
                "- Latest available major version\n\n"
                "If no dependencies need major updates, say NONE.\n"
                "End your response with the full list in this exact format:\n"
                "OUTDATED_DEPS: package1 current1 latest1, package2 current2 latest2, ...\n"
                "Or: OUTDATED_DEPS: NONE"
            ),
            "model": None,
            "timeout": 300,
            "retry": {"max_attempts": 1},
            "outputs": [],
            "requires": [],
            "extract": {},
            "status_label": "auditing dependencies",
            "position": {"x": 0, "y": 150},
        },
        {
            "id": "updater",
            "type": "claude_agent",
            "name": "Update & Validate",
            "prompt_template": (
                "You are updating Flutter dependencies ONE BY ONE to their latest major versions.\n\n"
                "IMPORTANT RULES:\n"
                "- Update ONE dependency at a time in pubspec.yaml\n"
                "- After each update: run `flutter pub get`, then `dart analyze`, then `flutter build apk --debug`\n"
                "- If analyze or build fails after updating a dep:\n"
                "  1. Try to fix the breaking changes (API changes, deprecations, etc.)\n"
                "  2. Run analyze + build again after fixing\n"
                "  3. If you cannot fix it after a reasonable attempt, REVERT that dependency to its original version\n"
                "  4. Run `flutter pub get` again after reverting to restore clean state\n"
                "- After each successful update (or revert), `git add -A && git commit` with a descriptive message\n"
                "- Keep track of what was updated successfully and what had to be reverted\n\n"
                "After processing ALL dependencies, write a summary report:\n"
                "## Updated Successfully\n"
                "- package_name: old_version -> new_version\n\n"
                "## Failed to Update (reverted)\n"
                "- package_name: old_version -> attempted_version — reason for failure\n\n"
                "## No Changes Needed\n"
                "- (if applicable)\n\n"
                "End with: BUILD_STATUS: PASS or BUILD_STATUS: FAIL"
            ),
            "model": None,
            "timeout": 1800,
            "retry": {"max_attempts": 1},
            "resume_from": "audit",
            "outputs": [{"name": "build_status", "values": ["PASS", "FAIL"]}],
            "requires": [],
            "extract": {},
            "status_label": "updating dependencies",
            "position": {"x": 0, "y": 300},
        },
        {
            "id": "build_check",
            "type": "condition",
            "name": "Build OK?",
            "condition_field": "build_status",
            "branches": {"PASS": "create_pr", "FAIL": "emergency_fix"},
            "default_branch": "create_pr",
            "position": {"x": 0, "y": 450},
        },
        {
            "id": "emergency_fix",
            "type": "claude_agent",
            "name": "Emergency Fix",
            "prompt_template": (
                "The Flutter build is failing after dependency updates.\n\n"
                "1. Run `dart analyze` and `flutter build apk --debug` to see current errors\n"
                "2. Fix what you can\n"
                "3. If a specific dependency update is causing unfixable errors, revert JUST that dependency\n"
                "4. Run `flutter pub get` after any reverts\n"
                "5. Keep going until `flutter build apk --debug` passes\n"
                "6. Commit your fixes\n\n"
                "The build MUST pass. Revert problematic deps if needed.\n\n"
                "End with: FIXED: YES or FIXED: NO"
            ),
            "model": None,
            "timeout": 1200,
            "retry": {"max_attempts": 1},
            "resume_from": "updater",
            "outputs": [{"name": "fixed", "values": ["YES", "NO"]}],
            "requires": ["build_status"],
            "extract": {},
            "status_label": "fixing build errors",
            "position": {"x": 250, "y": 450},
        },
        {
            "id": "fix_check",
            "type": "condition",
            "name": "Fixed?",
            "condition_field": "fixed",
            "branches": {"YES": "create_pr", "NO": "fail"},
            "default_branch": "fail",
            "position": {"x": 250, "y": 600},
        },
        {
            "id": "create_pr",
            "type": "claude_agent",
            "name": "Create PR",
            "prompt_template": (
                "Create a pull request with all the dependency updates.\n\n"
                "1. Push the current branch to origin\n"
                "2. Create a PR with:\n"
                "   - Title: `chore: update Flutter dependencies`\n"
                "   - Body: Include a full report of what was updated, what was reverted, and why\n"
                "   - List all version changes\n"
                "3. The PR body should be a clear changelog\n\n"
                "Output the PR URL at the end."
            ),
            "model": None,
            "timeout": 300,
            "retry": {"max_attempts": 1},
            "resume_from": "updater",
            "outputs": ["pr_url"],
            "requires": [],
            "extract": {"pr_url": "regex:https://github\\.com/[^\\s)]+/pull/\\d+"},
            "status_label": "creating PR",
            "position": {"x": 0, "y": 750},
        },
        {
            "id": "done",
            "type": "end",
            "name": "Done",
            "status": "done",
            "position": {"x": 0, "y": 900},
        },
        {
            "id": "fail",
            "type": "end",
            "name": "Failed",
            "status": "failed",
            "position": {"x": 250, "y": 750},
        },
    ],
    "edges": [
        {"from": "start", "to": "audit"},
        {"from": "audit", "to": "updater"},
        {"from": "updater", "to": "build_check"},
        {"from": "emergency_fix", "to": "fix_check"},
        {"from": "create_pr", "to": "done"},
    ],
}


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO pipeline_templates (name, description, definition, created_at, updated_at) "
            "VALUES (:name, :description, CAST(:definition AS JSONB), NOW(), NOW())"
        ).bindparams(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            definition=json.dumps(TEMPLATE_DEF),
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM pipeline_templates WHERE name = :name").bindparams(
            name=TEMPLATE_NAME,
        )
    )
