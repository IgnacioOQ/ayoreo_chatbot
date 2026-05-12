# TODO Workflow
- status: active
- type: plan
- id: ayoreo_chatbot.todo_workflow
- description: Cross-session task backlog for the Ayoreo chatbot; each task is self-contained and can be picked up by a coding agent with kb_mcp MCP tool access.
- label: [planning, agent]
- injection: excluded
- volatility: evolving
- owner: agent
- last_checked: 2026-05-12
<!-- content -->
Cross-session task backlog. Tasks are added here when work started in a session cannot be completed immediately. Each task must be fully self-contained — a fresh agent should be able to pick it up using only the task body and the kb_mcp tools, with no additional context required.

This file is the per-repository instance of the `TODO_WORKFLOW_TEMPLATE.md` pattern from the knowledge base. It lives at the root of the working repository alongside `WORKLOG.md` and is intentionally **not registered with kb_mcp** — agents access it via the regular filesystem `Read`/`Edit` tools, not via `knowledge_base_*` calls.

**Agent rules (picking up tasks):**
1. Read each task in full before starting. If its preconditions are unmet, skip it and note the blocker.
2. After completing a task, delete its entire block from this file (from the `---` divider above the `##` header through the `---` divider below the last line of the task body).
3. After completing one or more tasks, assess whether a WORKLOG.md entry is warranted — see Phase 5 of `content/workflows/CODING_AGENT_MAIN_WORKFLOW.md`.
4. Confirm a task is still valid before executing; conditions may have changed since it was written.

**Adding tasks (session authors):**
- Copy the template below (without fences), fill in all fields, and insert it as a new `##` block above the Template section, preceded and followed by `---`.
- Be precise: include target file paths, specific tool calls, expected outcomes, and a verification step.
- Any `knowledge_base_update` call requires a current `content_hash` — capture it with a `knowledge_base_read` at execution time, not when writing the task.

---

## Migrate the Streamlit sanity_app to Firebase
- status: todo
- type: task
- id: todo.firebase_migration_sanity_app
- description: Execute the multi-phase migration of the dataset reviewer from Streamlit to a React + Vite SPA on Firebase Hosting with Firestore-backed proposed corrections.
- owner: agent
- blocked_by: []
- last_checked: 2026-05-12
<!-- content -->
**Context:** [sanity_app.py](sanity_app.py) is a Streamlit app reviewers use to verify semantic alignment between EN and AYO paragraphs/verses in `data/raw/ayoreoorg/aligned_ayoreoorg.json` and `data/raw/bible/aligned_bible.json`. The migration moves it to a hosted web app so multiple allowlisted reviewers can collaborate without local Python setup, while keeping the canonical JSON files in the repo as source of truth.

**Plan reference:** Full plan with locked architectural decisions and 10 sequenced subtasks lives at [docs/reference/FIREBASE_MIGRATION_PLAN.md](docs/reference/FIREBASE_MIGRATION_PLAN.md). Read it in full before starting — do not re-derive the design from this stub.

**Preconditions:**
- Maintainer is ready to perform `task_1` (Firebase project provisioning) themselves; this is a `human` task in the plan and cannot be delegated to the agent.
- Allowlist of reviewer emails has been collected.

**Steps:**
1. Read [docs/reference/FIREBASE_MIGRATION_PLAN.md](docs/reference/FIREBASE_MIGRATION_PLAN.md) in full.
2. Execute tasks `firebase_migration_sanity_app.task_1` through `task_10` in order. Respect each task's `blocked_by` chain and `owner` field (some are `human`, most are `agent`).
3. Load the KB context references embedded in the plan as each task reaches them — do not preload all of them.
4. After completing each task, update its `status` field in the plan from `todo` to `done` (or `in-progress` while working).

**Verification:** All ten subtasks in [docs/reference/FIREBASE_MIGRATION_PLAN.md](docs/reference/FIREBASE_MIGRATION_PLAN.md) have `status: done`, the production URL is reachable by an allowlisted reviewer, one full reviewer-edit → maintainer-approve → export-to-JSON round trip has landed in `aligned_*.json`, and [README.md](README.md) documents the new workflow.

**On completion:** Delete this entire task block from TODO_WORKFLOW.md (from the `---` above the `##` header to the `---` below the last line).

---

## Task Template

Copy the block below (without the outer fences), fill in all fields, and insert it as a new `## [Task Title]` task block.

````markdown
## [Task Title]
- status: todo
- type: task
- id: todo.[short_id]
- description: One-sentence description of what this task accomplishes.
- owner: agent
- blocked_by: []
- last_checked: {{YYYY-MM-DD}}
<!-- content -->
**Context:** Why this task exists and what triggered it. Include the KB path or repo file path it operates on.

**Preconditions:** Any state that must be true before starting (prior tasks complete, files present, etc.). Write `none` if there are none.

**Steps:**
1. (Include specific tool calls where possible, e.g., `knowledge_base_read(path="content/...", sections=["..."])`)
2. ...

**Verification:** How to confirm the task is complete (e.g., a grep that should return one match, a status field that should read `done`).

**On completion:** Delete this entire task block from TODO_WORKFLOW.md (from the `---` above the `##` header to the `---` below the last line).
````
