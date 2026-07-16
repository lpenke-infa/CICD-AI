# IICS CICD-AI Automation Suite

AI-powered automation for Informatica Intelligent Cloud Services (IICS) with conversational Slack interface powered by Claude Opus 4.8.

> 📘 **New User?** Start with **[SETUP_GUIDE.md](SETUP_GUIDE.md)** for complete installation instructions from scratch.
>
> 💬 **Just using the bot?** See the **[USER_MANUAL.md](USER_MANUAL.md)** for a day-to-day guide to chatting with the Slack assistant.

---

## What This Does

Automates end-to-end IICS operations through a conversational Slack bot:

1. **Pre-Migration Validation** - Verify assets and connections before migration
2. **CI/CD Migration** - Automated 8-step Git-based migration between environments  
3. **Post-Migration Validation** - Verify successful migration with reports
4. **IDMC Operations** - Query, manage, and tag assets via natural language *(Development - In Progress)*

**Example:**
```
You: Run migration with config dev_to_qa.json
Bot: [Executes 8-step migration with real-time updates]
     ✅ Migrated 25 assets from Dev → QA

You: How many mappings have tag "Production"?
Bot: 📊 Total count: 156 items

You: List them all
Bot: [Generates Excel report with 156 mappings]
```

---

## Quick Start

### Prerequisites
- Python 3.9+ (3.11 recommended)
- Git installed
- IICS access credentials
- Slack workspace (for bot interface)

### Installation

```bash
# 1. Navigate to project
cd CICD-AI

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (.env file)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
ANTHROPIC_BEDROCK_BASE_URL=https://your-bedrock-endpoint
ANTHROPIC_AUTH_TOKEN=your-auth-token

# 5. Run the bot
python agent.py
```

**See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup instructions.**

---

## Project Structure

```
CICD-AI/
├── agent.py                   # Main Slack bot with Claude Opus 4.8
├── requirements.txt           # Python dependencies
├── .env                       # Environment configuration
├── README.md                  # This file (overview)
├── SETUP_GUIDE.md             # Complete setup guide
├── USER_MANUAL.md             # Day-to-day user guide for the Slack bot
├── system_prompt_v*.txt       # Versioned system prompts (v3 current)
│
├── Database/                  # SQLite databases (deployments.db, idmc_credentials.db)
│
├── CICDMigration/             # 8-step migration workflow
│   └── README.md              # → Detailed migration docs
│
├── PreMigrationCheck/         # Pre-migration validation
│   └── README.md              # → Detailed validation docs
│
├── PostMigrationCheck/        # Post-migration validation
│   └── README.md              # → Detailed validation docs
│
├── IDMCFunctionalities/       # 35 IDMC API functions
│   └── README.md              # → Detailed IDMC API docs
│
├── tools/                     # Modular tool wrappers (@tool + execute_*)
├── common/                    # Shared config validation
├── Configs/                   # Configuration templates
├── docs/                      # Documentation assets
│   └── images/                # Screenshots for USER_MANUAL.md
├── Logs/                      # Runtime logs
└── Reports/                   # Generated Excel reports
```

### Module Overview

| Module | Purpose | Files | Functions | Details |
|--------|---------|-------|-----------|---------|
| **CICDMigration** | Git-based asset migration (8 steps) | 13 | 34 | [README](CICDMigration/README.md) |
| **PreMigrationCheck** | Validate assets before migration | 8 | 14 | [README](PreMigrationCheck/README.md) |
| **PostMigrationCheck** | Verify migration success | 6 | 10 | [README](PostMigrationCheck/README.md) |
| **IDMCFunctionalities** | IDMC API operations (35 functions) — *Development - In Progress* | 2 | 35 | [README](IDMCFunctionalities/README.md) |
| **tools** | LangChain tool wrappers used by the bot | 5 | 12 | — |
| **common** | Shared config validation | 2 | 15 | — |

---

## Key Features

### 🤖 AI-Powered Conversational Interface
- Natural language queries via Slack
- Claude Opus 4.8 understands intent and context
- Interactive configuration collection
- Real-time progress updates

### 🔄 Complete Migration Workflow
```
Pre-Migration Check → CICD Migration (8 steps) → Post-Migration Validation
```

### 🏷️ Intelligent Asset Management
- Tag-based asset filtering
- Automatic project/folder creation
- Smart tagging (filters non-taggable types)
- Excel report generation

### 🔐 Enterprise-Ready
- Retry logic with exponential backoff
- Comprehensive logging
- Database audit trail (optional)
- Session memory per Slack channel

---

## Usage Examples

### 1. Pre-Migration Check
```
You: Run pre-migration check with config dev_to_qa.json

Bot: 🔍 Starting Pre-Migration Check...
     ✅ Logged into Source Org
     📊 Found 150 assets with tags: ["PreMigration"]
     ✅ All connections available in target
     📄 Report generated: pre_migration_20260628.xlsx
     
     Would you like to proceed with migration? (yes/no)
```

### 2. CICD Migration
```
You: yes

Bot: 🚀 Starting CI/CD Migration...
     Step 1/8: 🔐 Authenticating to Source...
     Step 2/8: 🏷️  Retrieving Tagged Assets...
     Step 3/8: 🔐 Authenticating to Target...
     Step 4/8: 📁 Creating Projects/Folders...
     Step 5/8: 🌿 Transferring Assets via Git...
     Step 6/8: ⬇️  Pulling Assets to Target...
     Step 7/8: 🏷️  Applying Tags...
     Step 8/8: 💾 Recording in Database...
     
     🎉 MIGRATION COMPLETED!
     • 150 assets migrated
     • Dev → QA
     • Commit: abc12345
     
     Would you like to run post-migration validation? (yes/no)
```

### 3. Post-Migration Validation
```
You: yes

Bot: 🔧 Starting Post-Migration Validation...
     ✅ All 150 assets found in target
     ✅ All tags applied correctly
     📄 Report: post_migration_20260628.xlsx
     
     ✅ Migration validated successfully!
```

### 4. IDMC Queries
```
You: How many mappings are in Production folder?
Bot: 📊 Total count: 45 items

You: List all mapping tasks with tag "Release_v2"
Bot: 📊 Found 23 items
     Report: IDMCFunctionalities_20260628.xlsx
     [Excel file uploaded]

You: Tag asset abc123 with "Validated"
Bot: ✅ Successfully tagged 1 asset!
```

### 5. Upload & Run
```
You: [Uploads config_prod.json to Slack]

Bot: ✅ Configuration file saved: config_prod.json
     
     What would you like to do?
     1️⃣ Run pre-migration check
     2️⃣ Run CI/CD migration
     3️⃣ Run post-migration validation
     4️⃣ Just keep it for later
```

---

## Configuration

### Environment Variables (.env)

The application reads only these four environment variables:

```env
# Slack Configuration (Required)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Claude AI Configuration (Required)
ANTHROPIC_BEDROCK_BASE_URL=https://your-bedrock-endpoint
ANTHROPIC_AUTH_TOKEN=your-auth-token
```

**Note:** IICS/IDMC credentials are **not** read from the environment. Supply them via configuration files (see `Configs/` templates below) or directly through the Slack chat. Optional database path overrides `DB_PATH` and `IDMC_CREDS_DB_PATH` are also available for the SQLite files.

### Configuration Files

Templates available in `Configs/`:
- `cicd_migration_config_template.json` - CICD migration settings
- `pre_migration_config_template.json` - Pre-migration validation
- `post_migration_config_template.json` - Post-migration validation

**Example CICD Config:**
```json
{
  "ProjectName": ["MyProject"],
  "IICS_SRC_username": "dev@example.com",
  "IICS_SRC_password": "password",
  "IICS_SRC_region": "dm-us",
  "IICS_TGT_username": "qa@example.com",
  "IICS_TGT_password": "password",
  "IICS_TGT_region": "dm-us",
  "PreMigration_Tag": ["ReadyForQA"],
  "PostMigration_Tag": ["Migrated"],
  "Git_Repository_URL": "https://github.com/org/repo.git",
  "Git_config_useremail": "user@example.com",
  "Git_config_username": "User Name",
  "Git_password": "github_token",
  "Git_SRC_Branch": "DEV",
  "Git_TGT_Branch": "QA"
}
```

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────┐
│       User (Slack Interface)        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Slack Bolt Handler (Socket Mode) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Claude Opus 4.8 (Intent & Context) │
│  • Understands natural language     │
│  • Routes to appropriate tool       │
│  • Maintains conversation context   │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┬──────────┬─────────────┐
       ▼                ▼          ▼             ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│   Pre-   │   │  CICD    │   │  Post-   │   │  IDMC    │
│Migration │   │Migration │   │Migration │   │Operations│
│  Check   │   │ (8 steps)│   │  Check   │   │(35 funcs)│
└──────────┘   └──────────┘   └──────────┘   └──────────┘
     │              │              │               │
     └──────────────┴──────────────┴───────────────┘
                    │
                    ▼
         ┌────────────────────┐
         │   IICS REST APIs   │
         │  (dm-us/eu/ap/em1) │
         └────────────────────┘
```

### CICD Migration 8-Step Workflow

See [CICDMigration/README.md](CICDMigration/README.md) for detailed workflow documentation.

```
1. 🔐 Authenticate to Source IICS
2. 🏷️  Retrieve Tagged Assets
3. 🔐 Authenticate to Target IICS
4. 📁 Create Projects and Folders
5. 🌿 Cherry-pick Assets via Git
6. ⬇️  Pull Assets to Target
7. 🏷️  Apply Post-Migration Tags
8. 💾 Record in Database (optional)
```

---

## Supported Asset Types

### Taggable Types (24+)
- **Data Integration:** DTEMPLATE, MTT, DSS, DTT, DMASK, DRS
- **Workflows:** TASKFLOW, WORKFLOW, SCHEDULE
- **Connections:** CONNECTION, AI_CONNECTION, AI_SERVICE_CONNECTOR
- **Business Services:** BSERVICE, PROCESS
- **Data Quality:** CLEANSE, PARSE, VERIFIER, DEDUPLICATE
- And 15+ more types

### Non-Taggable Types
- ⚠️ **PROJECT** - Projects cannot be tagged
- ⚠️ **FOLDER** - Folders cannot be tagged

**Note:** The bot automatically filters out PROJECT and FOLDER when tagging.

Full list of Git-migratable asset types in the `DICT_FILE_FORMAT` mapping in [CICDMigration/config.py](CICDMigration/config.py) (24 types).

---

## Logging & Reports

### Log Files (Logs/)
- `CICDMigration.log` - Migration operations
- `PreMigrationCheck.log` - Pre-migration validation
- `PostMigrationCheck.log` - Post-migration validation
- `IDMCFunctionalities.log` - IDMC API operations

**Format:**
```
2026-06-28 10:39:06 - MODULE - INFO - [function:line] - Message
```

### Excel Reports (Reports/)
- Pre-migration validation reports
- Post-migration validation reports
- IDMC query results
- Asset inventories with metadata

---

## Error Handling

### Retry Logic
- **Max Retries:** 3 attempts
- **Backoff:** Exponential (1s, 2s, 4s)
- **Applies to:** All IICS API calls and Git operations

### Exception Handling
- Descriptive error messages in Slack
- Full stack traces in log files
- Graceful degradation (e.g., optional database logging)
- Context about which operation failed

### Common Issues & Solutions

See [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting) for detailed troubleshooting.

| Issue | Solution |
|-------|----------|
| No assets found | Run pre-migration check first |
| Authentication failed | Verify credentials and region |
| Git operation failed | Check Git URL and token |
| Bot doesn't respond | Verify Slack tokens and Socket Mode |

---

## Security Best Practices

⚠️ **Important:**
1. **Never commit `.env` or config files with credentials** to version control
2. **Use Git tokens** with minimal required permissions
3. **Rotate credentials** regularly
4. **Review logs** before sharing (may contain sensitive info)
5. **Use environment variables** for sensitive data when possible

---

## Documentation

### Main Guides
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup from scratch
- **[README.md](README.md)** - This file (overview)

### Module-Specific Documentation
- **[CICDMigration/README.md](CICDMigration/README.md)** - 8-step migration workflow details
- **[PreMigrationCheck/README.md](PreMigrationCheck/README.md)** - Pre-migration validation
- **[PostMigrationCheck/README.md](PostMigrationCheck/README.md)** - Post-migration validation
- **[IDMCFunctionalities/README.md](IDMCFunctionalities/README.md)** - 35 IDMC API functions

---

## Support & Troubleshooting

1. **Check Logs:** Review log files in `Logs/` directory
2. **Setup Issues:** See [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting)
3. **Module Issues:** Check module-specific README files
4. **IICS Issues:** Contact your IICS administrator

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **AI/LLM** | Claude Opus 4.8 (via Bedrock gateway, OpenAI-compatible endpoint) |
| **LLM Client** | `langchain_openai.ChatOpenAI` pointed at the gateway `base_url` |
| **Bot Framework** | Slack Bolt SDK (Socket Mode) |
| **Language** | Python 3.9+ |
| **AI Framework** | LangChain |
| **Version Control** | Git |
| **API Client** | requests, httpx |
| **Report Generation** | pandas, openpyxl |
| **Config Validation** | pydantic |
| **Database** | SQLite (built-in `sqlite3`, no external server) |

---

## Statistics

| Metric | Value |
|--------|-------|
| **Total Python Files** | 37 (excluding `__pycache__`) |
| **Total Lines of Code** | ~8,855 |
| **Total Functions** | ~150 |
| **Supported Asset Types** | 70+ (IDMC queries); 24 Git-migratable |
| **IDMC API Functions** | 35 |
| **Migration Steps** | 8 |

---

## License

Internal use only - contact your organization for usage terms.

---

## Quick Reference Commands

### Bot Commands (via Slack)

```
# Greetings
"hello" / "hi" → Welcome menu

# Pre-Migration
"run pre-migration check with config dev_to_qa.json"
"pre-migration check"

# CICD Migration
"run migration with config dev_to_qa.json"
"migrate with config file demo.json"

# Post-Migration
"run post-migration validation"
"validate migration"

# IDMC Queries
"how many mappings?"
"list all assets with tag Production"
"show me all connections"
"tag asset abc123 with Release_v2"
"create project DataMigration"
"show all secure agents"

# File Upload
[Upload .json config file] → Bot saves and asks what to do
```

---

**Ready to automate your IICS workflows? Start with [SETUP_GUIDE.md](SETUP_GUIDE.md)!** 🚀
