# Firebase Migration Plan — Sanity App
- status: in-progress
- type: plan
- id: firebase_migration_sanity_app
- description: Migrate the Streamlit-based dataset sanity_app to a React + Vite SPA on Firebase Hosting with Google Auth allowlist, Firestore-backed proposed-corrections workflow, and an export-to-JSON pipeline that keeps the repo's aligned_*.json files as the canonical source of truth.
- label: [planning, firebase, frontend, infrastructure]
- injection: informational
- volatility: evolving
- scope: project-specific
- repository: [ayoreo_chatbot]
- last_checked: 2026-05-12
<!-- content -->

Migrate [sanity_app.py](../../sanity_app.py) — the Streamlit dataset reviewer used to verify semantic alignment between EN and AYO paragraphs/verses in `aligned_ayoreoorg.json` and `aligned_bible.json` — to a hosted web app on Firebase Hosting. The new app uses React + Vite, Google Sign-In restricted to an allowlist of trusted reviewers, and Firestore to collect *proposed corrections* without disturbing the canonical JSON files in the repo. A maintainer-run export script applies approved proposals back to the JSON files, which remain the source of truth for the training pipeline.

## Architectural decisions (locked)

- **Access**: allowlisted reviewers, Google Sign-In, enforced both client-side (UX) and via Firestore security rules.
- **Source of truth**: `data/raw/.../aligned_*.json` in the git repo remain canonical. Firestore stores a *snapshot* + *proposed corrections* per story. A manual export step applied by a maintainer reconciles Firestore proposals back to JSON, committed via normal git review.
- **Frontend stack**: React + Vite, deployed to Firebase Hosting (static). Matches the KB norm in `content/workflows/DEPLOY_FIREBASE_WORKFLOW.md` and `content/reference/FIREBASE_PLANNING_WEBAPP_REF.md`.
- **Firestore granularity**: one document per story under `datasets/{dataset_id}/stories/{story_id}`; proposals live in a subcollection `…/proposals/{reviewer_uid}` so concurrent reviewers never clobber each other. Each story document averages ~35 KB (max ~1 MB Firestore limit, safely under).
- **Cost model**: low — ~900 total story docs (759 bible + 132 ayoreoorg), reads dominated by reviewers paging through stories, writes only on save. Firestore free tier should cover early use.

<!-- Dynamic Context Loads:
     The tasks below reference these KB documents for execution-time guidance:
     - content/workflows/DEPLOY_FIREBASE_WORKFLOW.md  — end-to-end Firebase deploy recipe
     - content/reference/FIREBASE_PLANNING_WEBAPP_REF.md  — Vite scaffold, Firestore patterns, persistence pitfalls
     - content/reference/FIREBASE_DEFINITIONS_REF.md  — project association, CLI gotchas, security
     - content/reference/FIREBASE_PRIVACY_REF.md  — Firestore rules limits and admin-access gap
     Load lazily at the task that needs them; do not preload all four.
-->

<!-- Knowledge Capture:
     This plan touches well-trodden Firebase patterns already captured in the KB.
     Likely capture opportunities:
     - Update DEPLOY_FIREBASE_WORKFLOW.md if any step turns out wrong or incomplete for a non-Eikasia repo.
     - New how-to candidate: "Migrate a Streamlit data-annotation app to React + Firestore" — generalizable
       if other Streamlit reviewer tools follow. Scaffold only if a second such migration is on the horizon.
-->

---

## Provision Firebase project and enable services
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_1
- owner: human
- estimate: 1h
- blocked_by: []
<!-- content -->

> **Load context:** `mcp__kb_mcp__knowledge_base_read(path="content/reference/FIREBASE_DEFINITIONS_REF.md")`

Create a new Firebase project (e.g. `ayoreo-sanity`) under the appropriate GCP org. Enable:
- **Firebase Hosting** (static site).
- **Firestore** in Native mode, region `us-central1` (default; check the FIREBASE_DEFINITIONS_REF.md cost notes).
- **Firebase Authentication** with the **Google** provider.

Add the maintainer's email and `ignacioojea@gmail.com` to the Auth allowlist (a Firestore-stored list — see task_3). Confirm `firebase login`, `firebase projects:list`, and `firebase use ayoreo-sanity` all succeed locally. Capture the project ID and web-app config (`apiKey`, `authDomain`, `projectId`, etc.) into `.env.local` (see task_2).

**Exit criterion:** project exists, Firestore + Hosting + Google Auth are enabled, CLI is authenticated against the project.

---

## Scaffold the Vite + React + Firebase SDK frontend
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_2
- owner: agent
- estimate: 2h
- blocked_by: [firebase_migration_sanity_app.task_1]
<!-- content -->

> **Load context:** `mcp__kb_mcp__knowledge_base_read(path="content/reference/FIREBASE_PLANNING_WEBAPP_REF.md", sections=["3. Project Scaffold", "4. Firebase Setup", "5. Firebase Auth + Firestore in React"])`

Create a new top-level directory `webapp/` in the repo (sibling to `src/`, `data/`, etc. — the existing Python `src/` is for the training pipeline and stays untouched).

1. `npm create vite@latest webapp -- --template react`
2. `cd webapp && npm install firebase`
3. Add `webapp/.env.local` with the `VITE_FIREBASE_*` config keys from task_1.
4. Add `webapp/.gitignore` entries for `node_modules/`, `dist/`, `.env.local`.
5. Initialize Firebase config (`webapp/src/firebase.js`) — `initializeApp`, `getAuth`, `getFirestore` exports.
6. Run `firebase init hosting` from the repo root, pointing the public directory at `webapp/dist`, with SPA rewrites (`"rewrites": [{ "source": "**", "destination": "/index.html" }]`).

**Exit criterion:** `npm run dev` boots a blank React app that successfully `console.log`s a Firebase app instance. `firebase deploy --only hosting` deploys the placeholder to the live URL.

---

## Implement Google Sign-In with Firestore-backed email allowlist
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_3
- owner: agent
- estimate: 2h
- blocked_by: [firebase_migration_sanity_app.task_2]
<!-- content -->

Auth model:
- Client uses `signInWithPopup(GoogleAuthProvider)` (with redirect fallback per the KB pattern).
- Allowlist lives at `config/allowlist` (single Firestore doc with field `emails: string[]`).
- Client reads the allowlist after sign-in; if user's email is not present, they see a "request access" message and are signed out.
- Security rules enforce the allowlist server-side — see task_4.

Add a minimal `<AuthGate>` wrapper component that renders `<SignIn />` for unauthenticated users, a "not authorised" screen for signed-in users absent from the allowlist, and the app shell otherwise. Wire `onAuthStateChanged` for session persistence.

**Exit criterion:** an allowlisted account can sign in and see a placeholder dashboard; a non-allowlisted account is rejected with a clear message both client-side and (in DevTools network logs) at the Firestore-rules layer.

---

## Define Firestore schema and security rules
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_4
- owner: agent
- estimate: 2h
- blocked_by: [firebase_migration_sanity_app.task_3]
<!-- content -->

> **Load context:** `mcp__kb_mcp__knowledge_base_read(path="content/reference/FIREBASE_PRIVACY_REF.md", intro_only=True)`

Schema:

```
config/allowlist                                  # { emails: [...], updatedAt }
datasets/{dataset_id}                              # { name, source_path, snapshot_version, updatedAt }
datasets/{dataset_id}/stories/{story_id}           # canonical snapshot from JSON (read-only to reviewers)
datasets/{dataset_id}/stories/{story_id}/proposals/{reviewer_uid}
    # { body_decomposition, alignment_map, correction_notes, status, createdAt, updatedAt, reviewerEmail }
```

`dataset_id` values: `ayoreoorg`, `bible`. `story_id` matches the existing JSON keys (e.g. `bible__gen-1`).

`status` on a proposal is one of: `draft` | `submitted` | `approved` | `dismissed` | `applied`.

Security rules (`firestore.rules`):
- `config/allowlist`: read for any signed-in allowlisted user; write only via console.
- `datasets/{ds}/stories/{s}`: read for allowlisted users; write only via maintainer service account (used by the seed script).
- `datasets/{ds}/stories/{s}/proposals/{uid}`: read for allowlisted users; create/update only when `request.auth.uid == uid` AND email is in allowlist; transition to `approved`/`dismissed`/`applied` only by maintainer (gated by a `roles` field on the user's allowlist entry, or a hardcoded `maintainer_uids` list in rules).

Use the Firebase emulator (`firebase emulators:start --only firestore`) plus the Rules unit test framework to add at least four rules tests: allowlisted-read, non-allowlisted-blocked, own-proposal-write, cross-user-proposal-blocked.

**Exit criterion:** rules deployed, emulator tests pass, manual round-trip from a signed-in browser confirms reads work and unauthorised writes are rejected.

---

## Build the JSON-to-Firestore seed script
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_5
- owner: agent
- estimate: 3h
- blocked_by: [firebase_migration_sanity_app.task_4]
<!-- content -->

Create `scripts/seed_firestore.py` (Python, using `firebase-admin` SDK with a service-account key):

1. Read `data/raw/ayoreoorg/aligned_ayoreoorg.json` and `data/raw/bible/aligned_bible.json`.
2. Upsert one document per story under `datasets/{dataset_id}/stories/{story_id}` with fields: `title_en`, `title_ayo`, `url_en`, `url_ayo`, `type`, `section`, `body_en`, `body_ayo`, `body_decomposition`, `alignment_map`, `snapshot_version` (git SHA of HEAD when seeded), `seededAt`.
3. Use **batched writes** (max 500 ops per batch, per the Firestore SDK limit) — never write in a per-doc loop. This is mandated by the project workflow's "Batch over loops" rule.
4. Write a top-level `datasets/{dataset_id}` doc with metadata (`source_path`, `snapshot_version`, count, `seededAt`).
5. Make the script idempotent: re-running with the same `snapshot_version` skips unchanged stories (compare a content hash).

Document the script in [README.md](../../README.md) under a new "Sanity App" section (added in task_10). Add the service account key path to `.env` and update `.env.example`.

**Exit criterion:** seeding both datasets completes in under five minutes; story counts in Firestore match the JSON files (132 + 759 = 891 stories); a second run with no JSON changes performs zero writes.

---

## Port the sanity_app UI to React
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_6
- owner: agent
- estimate: 6h
- blocked_by: [firebase_migration_sanity_app.task_5]
<!-- content -->

Recreate the Streamlit UI from [sanity_app.py](../../sanity_app.py) as React components. Layout mirror:

| Streamlit element                          | React component                          |
| :----------------------------------------- | :--------------------------------------- |
| `st.selectbox` dataset / section filter    | `<Sidebar />` with `<DatasetPicker />`, `<SectionFilter />`, `<StoryList />` |
| `st.metric` row (type / section / narrator) | `<StoryHeader />`                        |
| Side-by-side `st.text_area` EN/AYO bodies  | `<BodyView />` (two read-only panes)     |
| `st.expander` per alignment group          | `<AlignmentGroupCard />`                 |
| Parallel EN/AYO chunk `st.text_area`s      | `<ChunkEditor />` inside each card       |
| `alignment_map` JSON textarea              | `<AlignmentMapEditor />` with JSON-lint  |
| `correction_notes` textarea                | `<NotesField />`                         |
| "Save Corrections to Disk" button          | `<ProposalActions submit />`             |

Data flow:
- On mount and on `selected_story` change: subscribe (`onSnapshot`) to both the canonical story doc and the current user's proposal doc.
- Initialize editor state from the user's existing draft proposal if present, else from the canonical snapshot.
- A debounced auto-save (500–1000 ms) writes the proposal as `status: "draft"` so reviewers don't lose work; an explicit **Submit for Review** button flips status to `submitted`.
- Show `⚠️` next to stories in the sidebar where the canonical decomposition lengths mismatch (mirroring `has_mismatch` in the current app).
- Show a small badge per story when the current reviewer has a draft/submitted proposal.

**Beware the Firestore persistence pitfalls** documented in `FIREBASE_PLANNING_WEBAPP_REF.md` section 12 — particularly the async-write race (1), the `useEffect`/save infinite loop (2), `setDoc` full-replacement (7), and `onSnapshot` firing multiple times (6). Adopt the patterns from that section verbatim rather than reinventing them.

**Exit criterion:** running locally against the seeded Firestore, an allowlisted reviewer can browse all 891 stories, edit any chunk, type a JSON alignment map, write notes, and see their draft persist across page reloads. Two reviewers signed into the same story do not see each other's drafts.

---

## Implement proposal submission and maintainer triage
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_7
- owner: agent
- estimate: 3h
- blocked_by: [firebase_migration_sanity_app.task_6]
<!-- content -->

Reviewer side:
- **Submit for Review** button transitions the proposal from `draft` → `submitted`, locks the editor (read-only until the maintainer responds), and shows a banner ("Awaiting maintainer review").
- **Withdraw** button transitions `submitted` → `draft` so the reviewer can keep editing.

Maintainer side (gated by `maintainer_uids` in rules — added in task_4):
- A `/review` route that lists all `submitted` proposals across datasets, grouped by story.
- Each row shows a diff view (canonical vs. proposed) for `body_decomposition`, `alignment_map`, and `correction_notes`.
- Actions: **Approve** (status → `approved`), **Dismiss** (status → `dismissed` with optional reason). Approved proposals queue up for the export script (task_8).

Use a minimal diff component (e.g. `react-diff-viewer-continued` or a hand-rolled per-chunk diff — pick whichever is lighter and consistent with the rest of the dependency footprint).

**Exit criterion:** the maintainer can see at least one round-trip of (reviewer-edits → submit → approve → status visible to reviewer) entirely in the deployed app.

---

## Build the Firestore-to-JSON export pipeline
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_8
- owner: agent
- estimate: 3h
- blocked_by: [firebase_migration_sanity_app.task_7]
<!-- content -->

Create `scripts/export_proposals.py` — the bridge that re-establishes the JSON files as the canonical SoT.

Behavior:
1. Read all proposals where `status == "approved"` across both datasets.
2. Load the relevant `aligned_*.json` from disk.
3. For each approved proposal, apply its `body_decomposition`, `alignment_map`, and `correction_notes` to the matching `story_id` entry. Refuse to apply if the canonical doc's `snapshot_version` has changed since the proposal was created (force the reviewer to refresh first) — this prevents silently overwriting unrelated updates.
4. Write a diff summary to stdout: which stories changed, which fields, and how many chunks were rewritten.
5. **Do not stage or commit** (per the project workflow rule). Print `git add` / `git commit` commands for the maintainer to run after reviewing the diff.
6. On success, transition each applied proposal to `status: "applied"` with `appliedAt` and `appliedBy` (the maintainer's email) so it disappears from the `/review` queue.

Add a `--dry-run` flag that prints the diff summary without writing files or mutating Firestore.

**Exit criterion:** running `python scripts/export_proposals.py --dry-run` on at least one approved test proposal prints a clean diff; without `--dry-run` the JSON file changes match the diff and `git diff` shows exactly the expected edits.

---

## Deploy to production and run end-to-end verification
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_9
- owner: human
- estimate: 2h
- blocked_by: [firebase_migration_sanity_app.task_8]
<!-- content -->

> **Load context:** `mcp__kb_mcp__knowledge_base_read(path="content/workflows/DEPLOY_FIREBASE_WORKFLOW.md", sections=["13. Build and Deploy", "15. Verification Checklist"])`

1. `cd webapp && npm run build`
2. `firebase deploy --only hosting,firestore:rules`
3. Visit the hosted URL, sign in as an allowlisted account, and walk through the verification checklist in `DEPLOY_FIREBASE_WORKFLOW.md` §15 — adapted to this app's scope (skip Calendar OAuth, skip Capacitor).
4. End-to-end smoke test: edit a known story, submit, approve from a second browser session, run the export script locally, confirm the JSON diff matches the edits, commit.
5. Confirm Firestore rules block: (a) non-allowlisted users from reading any data, (b) a signed-in reviewer from writing to another reviewer's proposal doc, (c) non-maintainers from transitioning a proposal to `approved`.

**Exit criterion:** production URL is reachable, an external reviewer (one of the allowlisted emails on a fresh device) completes the loop, and the export script lands a real correction back in `aligned_*.json`.

---

## Decommission the Streamlit app and update documentation
- status: todo
- type: task
- id: firebase_migration_sanity_app.task_10
- owner: human
- estimate: 1h
- blocked_by: [firebase_migration_sanity_app.task_9]
<!-- content -->

Once the Firebase app has been verified for at least one full reviewer cycle:

1. Move [sanity_app.py](../../sanity_app.py) to `scripts/legacy/sanity_app.py` with a header comment pointing to the new app. Do not delete — it remains a useful offline fallback for solo work.
2. Update [README.md](../../README.md): replace the `streamlit run sanity_app.py` line with the production URL and a short "Reviewer workflow" subsection covering sign-in → edit → submit. Keep the legacy command in an "Offline reviewer (legacy)" subsection.
3. Add a new section to [README.md](../../README.md) titled **Sanity App (Firebase)** covering: production URL, allowlist management, seed script usage, export script usage, where Firestore lives, and the GCP project ID.
4. Add `WORKLOG.md` entry per the project workflow.
5. Consider whether `IMPROVE_SM_PLAN.md` (the existing planning doc in this folder) overlaps with this one — if so, link or merge.

**Exit criterion:** README accurately describes the new workflow, the legacy script is preserved but clearly marked legacy, and a fresh reader can sign in and submit their first correction using only the README as guidance.
