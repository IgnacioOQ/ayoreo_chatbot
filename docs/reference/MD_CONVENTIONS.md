# Markdown-JSON Hybrid Schema Conventions
- status: active
- type: guideline
- id: md_json_hybrid_schema_conventions
- label: [core]
<!-- content -->
This document defines the strict conventions for the **Markdown-JSON Hybrid Schema** used in this project for hierarchical task coordination and agentic planning.

The key insight is that every Markdown file following this schema can be **losslessly converted to JSON** and back. This enables:
- Clear, abstract protocol definitions
- Programmatic manipulation via JSON  
- Human-readable documentation via Markdown

## Core Principle
- status: active
<!-- content -->
The system uses **Markdown headers** to define the structural hierarchy (the nodes) and **YAML-style metadata blocks** (immediately following the header) to define structured attributes. The entire tree can be serialized to JSON with a `content` field preserving the prose.

## Schema Rules
- status: active
<!-- content -->

### 1. Hierarchy & Nodes
- status: active
<!-- content -->
- **Headers**: Use standard Markdown headers (`#`, `##`, `###`) to define the hierarchy.
- **Nesting**: 
    - `#` is the Root/Document Title (usually only one per file).
    - `##` are Top-Level Tasks/Features.
    - `###` are Subtasks.
    - And so on.
- **Implicit Dependency**: A header is implicitly dependent on its parent header.
- **Explicit Dependency (DAG)**: 
    - Use the `blocked_by` metadata field to define dependencies on other nodes (siblings, cousins, etc.).
    - Pass a list of IDs or relative paths to allow a single node to depend on multiple prior nodes.
    - **Example**: `blocked_by: [task-a, task-b]` implies this node cannot start until both 'task-a' and 'task-b' are done.

### 2. Metadata Blocks
- status: active
<!-- content -->
- **Location**: Metadata MUST be placed **immediately** after the header.
- **Separator**: There MUST be a `<!-- content -->` line between the metadata block and the content. This HTML comment acts as an unambiguous separator that is invisible when rendered but easy for parsers to detect.
- **Format**: A METADATA block. It works best as a bulleted list of key-value pairs.
- **Preferred Format**: A strict list of key-value pairs.

**Example:**

```markdown

## Implement User Auth
- status: in-progress
- type: plan
- owner: dev-1
- estimate: 3d
- blocked_by: []
<!-- content -->
This section describes the implementation details...
```

### 3. Allowed Fields
- status: active
<!-- content -->
The following fields are standard, but the schema allows extensibility.

| Field | Type | Description |
| :--- | :--- | :--- |
| `status` | `enum` | `todo`, `in-progress`, `done`, `blocked`, `recurring`, `active` **(Mandatory)**|
| `type` | `enum` | `agent_skill`, `log`, `guideline`, `plan`, `task`, `documentation` **(Mandatory)** |
| `owner` | `string` | The agent or user assigned to this (e.g., `dev-1`, `claude`) **(Optional)** |
| `estimate` | `string` | Time estimate (e.g., `1d`, `4h`) **(Optional)** |
| `blocked_by`| `list` | List of explicit dependencies (IDs or relative paths) **(Optional)** |
| `priority` | `enum` | `draft`, `low`, `medium`, `high`, `critical` **(Optional)** |
| `id` | `string` | Unique identifier for the node (e.g., `project.component.task`). Used for robust merging and dependency tracking. **(Optional)** |
| `last_checked` | `string` | This is the date of the last time this node was modified, including change of status. **(Optional)** |
| `label` | `list` | Array of strings (e.g., 'template', 'draft') **(Optional)** |

<!-- MERGED FROM NEWER VERSION -->

The following fields are standard, but the schema allows extensibility.

| Field | Type | Description |
| :--- | :--- | :--- |
| `status` | `enum` | `todo`, `in-progress`, `done`, `blocked`, `recurring`, `active` **(Mandatory)**|
| `type` | `enum` | `agent_skill`, `log`, `guideline`, `plan`, `task`, `documentation` **(Mandatory)** |
| `owner` | `string` | The agent or user assigned to this (e.g., `dev-1`, `claude`) **(Optional)** |
| `estimate` | `string` | Time estimate (e.g., `1d`, `4h`) **(Optional)** |
| `blocked_by`| `list` | List of explicit dependencies (IDs or relative paths) **(Optional)** |
| `priority` | `enum` | `draft`, `low`, `medium`, `high`, `critical` **(Optional)** |
| `id` | `string` | Unique identifier for the node (e.g., `project.component.task`). Used for robust merging and dependency tracking. **(Optional)** |
| `last_checked` | `string` | This is the date of the last time this node was modified, including change of status. **(Optional)** |
| `label` | `list` | Array of strings (e.g., 'template', 'draft') **(Optional)** |

### Type Definitions
- id: markdown_json_hybrid_schema_conventions.implement_user_auth.type_definitions
- status: active
- type: context
- last_checked: 2026-01-31
<!-- content -->
- **`agent_skill`**: (Capability) Defines a persona, specialized toolset, or prompting strategy.
- **`log`**: (Historical) Append-only records of actions, decisions, or outputs.
- **`guideline`**: (Normative) Static rules, conventions, and high-level documentation (read-only reference).
- **`plan`**: (Finite) A high-level objective with a clear beginning and end. Usually the root node.
- **`task`**: (Finite) A specific, actionable unit of work. Usually a sub-node of a plan.
- **`documentation`**: (Informational) General documentation, textbooks, or reference material.

For extended fields consider:
 - The key is entirely lowercase
 - The key has no spaces (words are separated with dash or underscore)
 - The value is single line

### Standard Labels
- id: markdown_json_hybrid_schema_conventions.standard_labels
- status: active
- type: context
- last_checked: 2026-02-23
<!-- content -->
Labels are lists of strings, allowing multiple keywords for a single node. The repository uses these standard labels:

- **`agent`**: Agent skills or configurations.
- **`planning`**: Project plans, roadmaps, or objective outlines.
- **`draft`**: Markdowns that are incomplete, under construction, or lack clarity.
- **`guide`**: Guidelines, instructions, or best practices.
- **`template`**: General content that needs to be specified for particular projects (e.g., `README.md`, `AGENTS.md` often serve as templates).
- **`core`**: Essential project documentation defining the foundation of the repository (e.g., `MD_CONVENTIONS.md`).
- **`infrastructure`**: Deployment, CI/CD, and Cloud resource documentation.
- **`frontend`**: Client-side application, UI, and usage documentation.
- **`backend`**: Server-side logic, parsing, dependency resolution, and MCP server documentation.
- **`reference`**: Textbooks, external manuals, or deep-dive reference materials for context injection.

### 4. Dependencies
- status: active
<!-- content -->
Dependencies are managed centrally in `dependency_registry.json`. 

**Do not add `context_dependencies` metadata to files.**

To add a dependency:
1.  Use `python manager/dependency_manager.py add <file> <dependency>` (if available).
2.  Or manually edit `dependency_registry.json`.

**Resolution Protocol**:
1.  **Registry First**: Tools and agents look up the current file in the registry to find its dependencies.
2.  **Recursive Resolution**: Dependencies are resolved recursively to build the full context.

### 5. Context & Description
- status: active
<!-- content -->
- Any text following the metadata block is considered "Context" or "Description".
- It can contain free-form Markdown, code blocks, images, etc.

## Examples
- status: active
<!-- content -->

### Valid Node
- status: active
<!-- content -->
```markdown

### Database Schema
- status: done
- owner: dev-2
- estimate: 1d
<!-- content -->
Set up PostgreSQL schema for users and sessions.
```

### Invalid Node (Metadata not immediate)
- status: active
<!-- content -->
```markdown

### Database Schema
- status: active
<!-- content -->
Some text here first.

- status: done

```
*Error: Metadata block must immediately follow the header.*

### Invalid Node (Bad indentation/METADATA)
- status: active
<!-- content -->
```markdown

### Database Schema
- status: active
- owner: dev-2
- estimate: 1d
<!-- content -->
status: done
owner: dev-2

```
*Warning: While some parsers might handle this, prefer bullet points `- key: value` for readability and stricter parsing.*

<!-- MERGED FROM NEWER VERSION -->

Set up PostgreSQL schema for users and sessions.
```

<!-- MERGED FROM NEWER VERSION -->

Some text here first.

- status: done

```
*Error: Metadata block must immediately follow the header.*

## Parsing Logic (for Developers)
- status: active
<!-- content -->
1. **Scan for Headers**.
2. **Look ahead** at the lines immediately following the header.
3. **Parse lines** that match the METADATA key-value pattern (`- key: value` or `key: value`) until the `<!-- content -->` separator or a non-matching line is found.
4. **Everything else** until the next header of equal or higher level is "Content".

> [!NOTE]
> The parser maintains backward compatibility with files using a blank line as separator, but all new files and migrations should use `<!-- content -->`.

## Tooling Reference
- status: active
<!-- content -->
The following Python scripts are available in `language/` to interact with this schema:

### 1. `language/md_parser.py`
- status: active
<!-- content -->
- **Purpose**: The core parser enabling **bidirectional MD ↔ JSON** transformation.
- **Key Classes**:
    - `MarkdownParser`: Parses `.md` files into a `Node` tree
    - `Node`: Tree node with `to_dict()`, `from_dict()`, and `to_markdown()` methods
- **Transformations**:
    - **MD → JSON**: `parser.parse_file("file.md")` → `root.to_dict()` → `json.dumps()`
    - **JSON → MD**: `json.loads()` → `Node.from_dict(data)` → `root.to_markdown()`
- **CLI Usage**: `python3 language/md_parser.py <file.md>`
- **Output**: JSON representation of the tree or validation errors.

### 2. `language/visualization.py`
- status: active
<!-- content -->
- **Purpose**: Visualizes the task tree in the terminal with metadata.
- **Usage**: `python3 language/visualization.py <file.md>`
- **Output**: Unicode tree visualization.

### 3. `language/operations.py`
- status: active
<!-- content -->
- **Purpose**: Manipulate task trees (merge, extend).
- **Usage**:
    - **Merge**: `python3 language/operations.py merge <target.md> <source.md> "<Target Node Title>" [--output <out.md>]`
        - Inserts the source tree as children of the specified target node.
    - **Extend**: `python3 language/operations.py extend <target.md> <source.md> [--output <out.md>]`
        - Appends the source tree's top-level items to the target tree's top level.

### 4. `language/migrate.py`
- status: active
<!-- content -->
- **Purpose**: Heuristically adds default metadata to standard Markdown headers to make them schema-compliant.
- **Usage**: `python3 language/migrate.py <file.md> [file2.md ...]`
- **Effect**: Modifies files in-place by injecting `- status: active` after headers that lack metadata.

### 5. `language/importer.py`
- status: active
<!-- content -->
- **Purpose**: Converts legacy documents (`.docx`, `.pdf`, `.doc`) into Markdown and auto-applies the Protocol.
- **Usage**: `python3 language/importer.py <file.docx> [file.pdf ...]`
- **Capabilities**:
    - **DOCX**: Preserves headers (Heading 1-3) if `python-docx` is installed. Fallbacks to text extraction.
    - **PDF**: Extracts text if `pypdf` or `pdftotext` is available.
    - **DOC**: Uses MacOS `textutil` for text extraction.

## Migration Guidelines
- status: active
<!-- content -->
When migrating existing documentation to this schema:
1. **Run the Migration Script**: Use `language/migrate.py` to add baseline metadata.
2. **Review and Refine**: Manually update the `status` fields (e.g., change `active` to `draft` or `deprecated` where appropriate) and add `owner` information.
3. **Structure Check**: Ensure the hierarchy makes sense as a task/node tree.

## Best Practices for AI Generation
- status: active
<!-- content -->
When generating or modifying files in this repository, AI agents MUST adhere to the following best practices to ensure system stability and parsing accuracy:

1.  **Always Generate IDs**: When creating new nodes (tasks, features, sections), always generate a unique `id` in the metadata (e.g., `id: component.subcomponent.task`). This ensures that references remain stable even if titles change.
2.  **Update Timestamps**: When modifying a node, update the `last_checked` field to the current date (ISO-8601).
3.  **Strict Spacing**: You **MUST** add a `<!-- content -->` separator line between the metadata block and the content. This is critical for the parser to distinguish between metadata and content lists.
    *   *Correct*:
        ```markdown
        ## Title
        - status: active
        <!-- content -->
        Content starts here...
        ```
    *   *Incorrect*:
        ```markdown
        ## Title
        - status: active
        Content starts here...
        ```
4.  **Use Allowed Fields**: Only use metadata keys explicitly listed in the "Allowed Fields" section (`status`, `type`, `owner`, `estimate`, `blocked_by`, `priority`, `id`, `last_checked`, `label`) unless you have a specific, documented reason to extend the schema.
