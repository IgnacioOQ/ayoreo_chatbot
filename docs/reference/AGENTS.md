# AGENTS.md
- status: active
- type: guideline
- context_dependencies: {"conventions": "MD_CONVENTIONS.md", "project_root": "README.md"}
<!-- content -->

## SHORT ADVICE
- status: active
<!-- content -->
- The whole trick is providing the AI Assistants with context, and this is done using the *.md files (AGENTS.md, AGENTS_LOG.md, and the AI_AGENTS folder)
- Make sure that when writing *.md files, you use the proper syntax protocol as defined in MD_CONVENTIONS.md. If necessary, you can always use the scripts in the language folder to help you with this.
- Learn how to work the Github, explained below.
- Keep logs of changes in AGENTS_LOG.md
- Make sure to execute the HOUSEKEEPING.md protocol often.
- Always ask several forms of verification, so because the self-loop of the chain of thought improves performance.
- Impose restrictions and constraints explicitly in the context.

## HUMAN-ASSISTANT WORKFLOW
- status: active
<!-- content -->
1. Open the assistant and load the ai-agents-branch into their local repositories. Do this by commanding them to first of all read the AGENTS.md file.
2. Work on the ASSISTANT, making requests, modifying code, etc.
3. IMPORTANT: GIT MECHANISM
    3.1. This is basically solved in Antigravity and VSCode, but Jules (and maybe Claude) push the changes into a newly generated branch. In my case, this is `jules-sync-main-v1-15491954756027628005`. **This is different from the `ai-agents-branch`!!**
    3.2. So what you need to do is merge the newly generated branch and the `ai-agents-branch` often. Usually in the direction from `jules-sync-main-v1-15491954756027628005` to `ai-agents-branch`. I do this by:
        3.2.1. Going to pull requests.
        3.2.2. New Pull request
        3.2.3. Base: `ai-agents-branch`, Compare: `jules-sync-main-v1-15491954756027628005` (arrow in the right direction).
        3.2.4. Follow through. It should allow to merge and there should not be incompatibilities. If there are incompatibilities, you can delete the `ai-agents-branch` and create a new one cloning the `jules-sync-main-v1-15491954756027628005` one. After deleting `ai-agents-branch`, go to the `jules-sync-main-v1-15491954756027628005` branch, look at the dropdown bar with the branches (not the link), and create a new copy.
4. It is very useful to use specialized agents for different sectors of the code. 
5. Enjoy!

## WORKFLOW & TOOLING
- status: active
<!-- content -->
*   **Documentation Logs (`AGENTS_LOG.md`):**
    *   **Rule:** Every agent that performs a significant intervention or modifies the codebase **MUST** update the `AGENTS_LOG.md` file.
    *   **Action:** Append a new entry under the "Intervention History" section summarizing the task, the changes made, and the date.

## DEVELOPMENT RULES & CONSTRAINTS
- status: active
<!-- content -->
1.  **Immutable Core Files:** Do not modify 
    *   If you need to change the logic of an agent or the model, you must create a **new version** (e.g., a subclass or a new file) rather than modifying the existing classes in place.
2.  **Consistency:** Ensure any modifications or new additions remain as consistent as possible with the logic and structure of the `main` branch.
3.  **Coding Conventions:** Always keep the coding conventions pristine.
4.  **Performance:** When interacting with databases (Vector DB, Graph) or APIs, **always prefer batch operations** over sequential loops. (e.g., use `vs.query([q1, q2])` instead of looping `vs.query(q1)`).

## CONTEXT FINE-TUNING
- status: active
<!-- content -->
You cannot "fine-tune" an AI agent (change its underlying neural network weights) with files in this repository. **However**, you **CAN** achieve a similar result using **Context**.

**How it works (The "Context" Approach):**
If you add textbooks or guides to the repository (preferably as Markdown `.md` or text files), agents can read them. You should then update the relevant agent instructions (e.g., `AI_AGENTS/specialists/LINEARIZE_AGENT.md` or `AI_AGENTS/specialists/CLOUD_SCHEDULER_AGENT.md`) to include a directive like:

> "Before implementing changes, read `docs/linearization_textbook.md` and `docs/jax_guide.md`. Use the specific techniques described in Chapter 4 for sparse matrix operations."

**Why this is effective:**
1.  **Specific Knowledge:** Adding a specific textbook helps if you want a *specific style* of implementation (e.g., using `jax.lax.scan` vs `vmap` in a particular way).
2.  **Domain Techniques:** If the textbook contains specific math shortcuts for your network types, providing the text allows the agent to apply those exact formulas instead of generic ones.

**Recommendation:**
If you want to teach an agent a new language (like JAX) or technique:
1.  Add the relevant chapters as **text/markdown** files.
    *   **Best Practice:** Organize these files using the **Markdown-JSON Hybrid Schema** (see `MD_CONVENTIONS.md`). This allows agents to understand the hierarchy of the concepts and metadata like `difficulty` or `topic`, and enables programmatic manipulation via JSON.
2.  Update the agent's instruction file (e.g., `AI_AGENTS/LINEARIZE_AGENT.md`) to reference them.
3.  Ask the agent to "Refactor the code using the techniques in [File X]".
