# Web-Based SOP Assistant – High-Level Architecture Notes

## 🧩 Problem Summary

We're planning to build an assistant that:
- Primarily searches **internal SOPs** (documents).
- Optionally looks on the **web** if internal info isn’t enough.
- Should be usable as a **web service**, not just via local CLI.

### 🚧 The Challenge

How can a web-based version still access SOPs, when every team has its own local/private/unique document setup?

---

## ✅ Solution Overview

We want a **flexible ingestion system** with **team-specific configuration**, so the web-based SOP Assistant can:

- Pull documents from various sources (GitHub, file paths, cloud APIs, etc.)
- Maintain per-team workspaces or configurations.
- Periodically update or sync those documents.
- Let teams control what their assistant “knows.”

---

## 🏗️ Architecture Sketch

```plaintext
[ Web UI ]
   |
[ FastAPI Server ]
   |
[ Document Loader Layer ]
   |       |       |
[Local FS][GitHub][Google Drive] ← Configurable
   |
[ Embed + Store in Vector DB ]
   |
[ RAG Pipeline (LLM + LangChain + Web Fallback) ]
```
---

## 🧠 How Different Teams Connect to SOPs

### 1. 🧩 Team Workspace Concept
- Each team has a workspace that stores:
- SOP document sources (local paths, GitHub repos, cloud drives)
- Embedding model/version
- Access credentials or tokens (if needed)

**Example YAML Configuration**

```yaml
team_name: sre-core
sources:
  - type: local
    path: /mnt/shared/sops/
  - type: github
    repo: git@github.com:company/sre-sops.git
    branch: main
    sync: hourly
  - type: drive
    folder_id: abc123
embedding_model: sentence-transformers/all-MiniLM-L6-v2
```

### 2. 🔌 Loaders
The document loader layer should support:

✅ Local file loaders (.md, .txt, .pdf)

✅ GitHub repo loaders (via API or clone)

✅ Google Drive loader (via service account)

✅ Custom loaders (e.g., Confluence, Notion, Jira, etc.)

All loader behavior is defined in the team's config.

### 3. 🚀 Onboarding Flow
When setting up a new team:
- Ask where their SOPs are stored
- What file types they use
- Any authentication details (tokens, service accounts)

Assistant will:
- Ingest docs once
- Periodically re-ingest or refresh embeddings

## 🌐 Web-Based Assistant in Action – Team Scenarios
**Team A – Local Setup**
- Mounts a shared NFS folder at /mnt/team-a-sops/
- Assistant runs in web UI, queries their files

**Team B – GitHub**
- Stores SOPs in a private GitHub repo: github.com/org/team-b-sops
- Assistant syncs via token and pulls updates daily

**Team C – Google Drive**
- SOPs are stored in a shared Drive folder
- Assistant loads them using a service account

## 🔐 Secure Web-Based Usage
To ensure privacy and security:
- Each team gets isolated logins and their own vector database/namespace
- No SOP data is shared across teams
- LLMs (e.g., Mistral via Ollama) run locally or on secure infrastructure

**Optional: Multi-Tenant Setup**
- Use separate containers or FastAPI workers per team
- Add authentication (JWT, OAuth, LDAP)
- Secure credentials and configs via vault or secrets manager
  
## 🧾 Summary
A web-based SOP Assistant can work securely and effectively for teams with varying documentation setups. To achieve this:
- Implement a flexible document ingestion system
- Use team-level configuration
- Allow scheduled updates or manual refresh
- Maintain secure isolation of all data and services


*This document was drafted with guidance from ChatGPT (OpenAI)*


