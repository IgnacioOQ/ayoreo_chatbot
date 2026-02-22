# Google Cloud & API Integration Guide
- status: active
- type: guideline
- context_dependencies: {"conventions": "MD_CONVENTIONS.md", "project_root": "README.md"}
<!-- content -->

This document serves as the authoritative guide for managing Google Cloud Platform (GCP) resources, API keys, and environment configurations for the MCMP Chatbot. It explains the relationship between the various Google services and how to effectively manage them in both local and deployed environments.

## Architecture & Relationships
- status: active
<!-- content -->

Understanding the distinction between resources is critical for billing and access control.

### 1. The Ecosystem Map
- **Google Cloud Platform (GCP)**: The overarching cloud provider. Projects here (like `mcmp-chatbot`) act as containers for resources (Service Accounts, APIs, Billing).
- **Google AI Studio**: Where Gemini API keys are generated. *Crucially*, keys generated here can be associated with *no project* (resulting in a default `gen-lang-client` project) or an *existing GCP project*.
- **Streamlit Cloud**: The hosting platform. It is *external* to Google but connects via secrets.

### 2. Service Separation
In this project, we use two distinct authentication methods for two different purposes:

| Feature | Service | Auth Method | Config Variable | Billing Source |
| :--- | :--- | :--- | :--- | :--- |
| **LLM Inference** | Gemini API | API Key | `GEMINI_API_KEY` | Determined by the key's creation project |
| **Database/Feedback** | Google Sheets | Service Account | `[gcp_service_account]` | `mcmp-chatbot` GCP Project |

> [!IMPORTANT]
> **Billing Discrepancy Risk**: If you create a Gemini API Key without selecting the `mcmp-chatbot` project, Google creates a shadow project (e.g., `gen-lang-client-XYZ`). Usage will be billed to that shadow project, not `mcmp-chatbot`. To consolidate, always select the specific project when creating keys in AI Studio.

## Environment & Secrets Management
- status: active
<!-- content -->

We use a "Split-Brain" configuration strategy to separate local development from production.

### 1. Local Development
- **File**: `.env` (for API Keys) and `.streamlit/secrets.toml` (for Service Accounts).
- **Mechanism**: 
    - `python-dotenv` loads `.env` into environment variables.
    - Streamlit automatically loads `.streamlit/secrets.toml`.
- **Best Practice**: NEVER commit `.env` or `.streamlit/secrets.toml` to Git.

### 2. Streamlit Cloud Deployment
- **Location**: App Dashboard → Settings → Secrets.
- **Mechanism**: Streamlit Cloud injects these secrets as environment variables (`os.environ`) at runtime.
- **Critical Rule**: You must manually verify that **BOTH** the `GEMINI_API_KEY` and the `[gcp_service_account]` block are present in the cloud secrets.
- **Reloading**: Changing secrets in the dashboard requires a **Reboot App** to take effect immediately.

## Troubleshooting Logs
- status: active
- type: log
<!-- content -->

### Issue: Billing Split (Jan 2026)
- **Problem**: Gemini usage was billed to `gen-lang-client-0023672537` while Sheets usage went to `mcmp-chatbot`.
- **Cause**: The `GEMINI_API_KEY` was created in Google AI Studio without linking it to the `mcmp-chatbot` project.
- **Fix**: Generated a new API Key in AI Studio, explicitly selecting `mcmp-chatbot` from the project dropdown.

### Issue: "API Key Expired" Loop
- **Problem**: After updating `.env` locally or Secrets on Cloud, the app still returned `400 API_KEY_INVALID`.
- **Cause**: The Python process (Streamlit server) loads environment variables *only on startup*. Hot-reloading checks code changes but not environment variable changes.
- **Fix**: Manually stop (Ctrl+C) and restart the Streamlit server (`streamlit run app.py`). On Cloud, use the "Reboot App" button.

### Issue: Secret Precedence
- **Problem**: Confusion over whether `secrets.toml` overrides `.env`.
- **Resolution**: Keeps things simple. Store *only* Service Account JSON in `secrets.toml` and *only* simple strings (API Keys) in `.env`. Do not duplicate keys.

## Common Workflows
- status: active
<!-- content -->

### How to Monitor Usage
1.  **For Gemini**: Go to [Google AI Studio](https://aistudio.google.com/) or the GCP Console for the project linked to your key.
2.  **For Sheets**: Go to GCP Console → APIs & Services → Enabled APIs → Google Sheets API.

### How to Rotate Keys
1.  Generate new key in AI Studio.
2.  Update `.env` (Local).
3.  Update Streamlit Cloud Secrets (Production).
4.  **Restart both servers**.
