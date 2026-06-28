# IICS CI/CD Automation Tool + IDMC Operations

Automated migration of Informatica Intelligent Cloud Services (IICS) assets between environments using Git-based version control with conversational Slack bot interface. Now includes comprehensive IDMC API operations for querying objects, managing tags, projects, schedules, users, and agents.

> 📘 **New User?** Start with [SETUP_GUIDE.md](SETUP_GUIDE.md) for step-by-step installation instructions from scratch.

## Overview

This tool automates the process of migrating IICS assets (mappings, taskflows, connections, etc.) from a source environment to a target environment using Git as the transport mechanism.

### Workflow

```
Source IICS → Retrieve Tagged Assets → Git Cherry-pick → Target IICS → Tag Migrated Assets
```

## Features

### CICD Migration Features
- **Tag-Based Asset Selection**: Retrieve assets using IICS tags
- **Git-Based Migration**: Uses Git branches for version control
- **Automatic Project/Folder Creation**: Creates target structure automatically
- **Post-Migration Tagging**: Tags migrated assets for tracking
- **Database Audit Trail**: Records migration history (optional)
- **Retry Logic**: Automatic retry with exponential backoff for API calls
- **Comprehensive Logging**: Timestamped logs with function-level tracing
- **Interactive Configuration**: Config file or manual input via Slack
- **Real-Time Updates**: Live progress updates for all migration steps
- **Session Memory**: Remembers last used config file per Slack channel

### IDMC Operations Features (Enhanced)
- **Query Objects**: Get any IDMC objects with advanced filtering
  - By type: `get_objects with type DTEMPLATE` (get all mappings)
  - By tag: `list assets with tag Production`
  - By path: `get objects in folder Project/Test`
  - Combined filters: `type=='MTT' and tags contains 'Dev'`
- **Count Queries**: Ask "how many mappings?" - returns count only (no Excel report)
- **List Queries**: Ask "list all mappings" - generates Excel report with all details
- **Smart Tagging**: Automatically filters out PROJECT/FOLDER types (they can't be tagged)
- **Context-Aware**: Remembers tags and filters from conversation
- **Manage Tags**: Add or remove tags from multiple assets at once
- **Manage Projects**: Create, update, or delete projects
- **Folder Management**: Create, update, delete folders
- **Get Schedules**: List and view schedule details
- **Get Users**: List organization users
- **Get Agents**: View secure agents and runtime environments
- **Conversational AI**: Claude Sonnet 4 understands natural language requests
- **Single Interface**: Both CICD and IDMC operations in one bot

## Prerequisites

- Python 3.7+
- Git installed and configured
- IICS access with appropriate permissions
- Network access to IICS regions and Git repository
- Slack workspace with bot (for Slack agent)
- Anthropic API access (for Slack agent)

## Project Structure

```
CICD_FINAL/
├── agent.py                    # Main Slack bot interface (CICD + IDMC)
├── run_cicd.py                # CLI wrapper for direct execution
├── .env                       # Environment variables (Slack/Anthropic tokens)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── CICDMigration/                      # CICD automation package
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Core orchestration
│   ├── logger.py             # Logging configuration
│   ├── login.py              # IICS authentication
│   ├── taggedAssets.py       # Asset retrieval
│   ├── cherrypick.py         # Git operations
│   ├── createProjectsAndFolders.py  # Target structure setup
│   ├── pull.py               # Asset import
│   ├── postMigrationTag.py   # Post-migration tagging
│   ├── database.py           # Audit logging
│   ├── config.py             # Configuration constants
│   ├── utils.py              # Utility functions
│   └── input_example.json    # Config template
└── IDMCFunctionalities/                      # IDMC operations package (NEW)
    ├── __init__.py           # Package initialization
    └── idmc_functions.py     # 30+ IDMC API wrapper functions
```

## Quick Start

### For New Users

Follow the complete setup guide: **[SETUP_GUIDE.md](SETUP_GUIDE.md)**

This includes:
- Installing Python and dependencies from scratch
- Creating and configuring Slack app
- Setting up environment variables
- Testing and troubleshooting

### For Experienced Users

1. **Extract** the project and navigate to directory
   ```bash
   cd CICD_Final
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** - Create `.env` file:
   ```env
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   ANTHROPIC_BEDROCK_BASE_URL=https://your-bedrock-endpoint
   ANTHROPIC_AUTH_TOKEN=your-auth-token
   ```

5. **Run the bot**
   ```bash
   python agent.py
   ```

## Configuration

Create a JSON configuration file with the following structure:

```json
{
    "ProjectName": ["YourProjectName"],
    
    "IICS_SRC_username": "source_username",
    "IICS_SRC_password": "source_password",
    "IICS_SRC_region": "dm-us",
    
    "IICS_TGT_username": "target_username",
    "IICS_TGT_password": "target_password",
    "IICS_TGT_region": "dm-us",
    
    "PreMigration_Tag": ["TAG1", "TAG2"],
    "PostMigration_Tag": ["MIGRATED"],
    
    "Git_Repository_URL": "https://github.com/org/repo",
    "Git_config_useremail": "user@example.com",
    "Git_config_username": "username",
    "Git_password": "git_token",
    
    "Git_SRC_Branch": "DEV",
    "Git_TGT_Branch": "QA",
    
    "Publish": 0,
    "logFileDir": "Logs"
}
```

### Configuration Parameters

| Parameter | Description |
|-----------|-------------|
| `ProjectName` | IICS project name (as array) |
| `IICS_SRC_*` | Source IICS credentials and region |
| `IICS_TGT_*` | Target IICS credentials and region |
| `PreMigration_Tag` | Tags to filter assets in source |
| `PostMigration_Tag` | Tags to apply after migration |
| `Git_Repository_URL` | Git repository URL |
| `Git_config_*` | Git user configuration |
| `Git_password` | Git personal access token |
| `Git_SRC_Branch` | Source branch name |
| `Git_TGT_Branch` | Target branch name |
| `logFileDir` | Directory for log files |

## Usage

### Slack Bot (Conversational)

Start the interactive Slack bot:

```bash
python agent.py
```

You should see:
```
⚡ IICS CI/CD Agent is live with Claude Sonnet 4!
📋 Features:
   • Config file or manual input
   • Interactive missing field collection
   • Real-time migration progress updates
   • Session memory for last used config
```

Then interact via Slack:

**User:** `Run CICD migration`

**Bot:** `Do you want to: 1. Use a config file 2. Provide details manually`

**User:** `Use config file input_internal.json`

**Bot:** `✅ Loaded config from: input_internal.json`

If missing fields:

**Bot:** `📝 Missing field: IICS_SRC_password. Source IICS password. What value should I use?`

**User:** `mypassword123`

**Bot:** `✅ Updated IICS_SRC_password in config file`

After all fields collected:

**Bot:** 
```
📋 Configuration to be used:
{
  "ProjectName": ["MyProject"],
  "IICS_SRC_username": "user@example.com",
  "IICS_SRC_password": "***",
  ...
}

✅ Proceed with migration? (yes/no)
```

**User:** `yes`

**Bot:** Real-time updates for each step:
```
🚀 Starting IICS CI/CD Migration
==================================================
Step 1/8: 🔐 Authenticating to Source IICS...
✅ Logged into Source: MySourceOrg
Step 2/8: 🏷️  Retrieving Tagged Assets from Source...
✅ Found 25 assets to migrate
Step 3/8: 🔐 Authenticating to Target IICS...
✅ Logged into Target: MyTargetOrg
Step 4/8: 📁 Creating Required Projects and Folders...
✅ Projects and folders ready
Step 5/8: 🌿 Cherry-picking Assets via Git...
✅ Git operations complete. Commit: abc12345
Step 6/8: ⬇️  Pulling Assets to Target Environment...
✅ Assets pulled successfully
Step 7/8: 🏷️  Applying Post-Migration Tags...
✅ Tags applied
Step 8/8: 💾 Recording Migration in Database...
✅ Database record created
==================================================
🎉 MIGRATION COMPLETED SUCCESSFULLY!
📊 Summary:
   • Assets Migrated: 25
   • Source Org: MySourceOrg
   • Target Org: MyTargetOrg
   • Commit Hash: abc1234567890def
==================================================
```

## Migration Steps

The tool performs the following steps automatically:

1. **Authenticate to Source IICS**: Login to source organization
2. **Retrieve Tagged Assets**: Get all assets with specified tags
3. **Authenticate to Target IICS**: Login to target organization
4. **Create Projects/Folders**: Ensure target structure exists
5. **Git Cherry-pick**: Cherry-pick assets from source to target branch
6. **Pull Assets**: Import assets into target IICS environment
7. **Apply Post-Migration Tags**: Tag migrated assets
8. **Record in Database**: Log migration details (optional)

## Supported Asset Types

The tool supports 24+ IICS asset types including:

### Taggable Types
- Mappings: `DTEMPLATE`, `MTT`
- Taskflows: `TASKFLOW`
- Connections: `CONNECTION`, `AI_CONNECTION`
- Service Connectors: `AI_SERVICE_CONNECTOR`
- Business Services: `BSERVICE`
- Processes: `PROCESS`
- Data Quality: `CLEANSE`, `PARSE`, `VERIFIER`
- Schedules: `SCHEDULE`
- And many more...

### Non-Taggable Types
- ⚠️ `PROJECT` - Projects cannot be tagged
- ⚠️ `FOLDER` - Folders cannot be tagged

**Note:** The bot automatically filters out PROJECT and FOLDER types when tagging.

See `CICDMigration/config.py` for the complete list.

## Slack Bot Features

### Intelligent Query Understanding

The bot understands context and intent:

**Count Queries** (returns count only):
```
You: how many mappings do we have?
Bot: 📊 Total count: 256 items
```

**List Queries** (generates Excel report):
```
You: list all mappings with tag "Production"
Bot: 📊 Found 45 items
     Report generated: IDMCFunctionalities_20260628_152318.xlsx
     [Excel file attached]
```

**Context Awareness**:
```
You: tag these assets with "DemoTest" [provides IDs]
Bot: ✅ Successfully tagged 7 asset(s)!

You: now list assets with that tag
Bot: [Automatically remembers "DemoTest" and lists only those 7 assets]
```

### Smart Tag Filtering

Automatically filters out unsupported types:
```
You: tag these 10 assets with "Test"
Bot: ⚠️ Skipped 2 unsupported asset(s) (PROJECT/FOLDER types cannot be tagged)
     ✅ Successfully tagged 8 asset(s)!
```

### Interactive Missing Field Collection

When fields are missing, the agent:
1. Identifies missing fields using validation
2. Asks one-by-one with helpful context
3. Parses response based on field type
4. Updates JSON file immediately after each field
5. Shows final config for confirmation

### Session Storage

Remembers your last config file per Slack channel:
- **User:** `Run migration again`
- **Bot:** `I found your last config file: input_internal.json. Do you want to use this file?`

### Security

- Passwords are masked (***) when displaying config
- Credentials stored in JSON file (not in session memory)
- Session only remembers last config file path
- .env file should not be committed to version control

## Error Handling

- **Automatic Retry**: API calls retry up to 3 times with exponential backoff
- **Detailed Logging**: All operations logged with timestamps and context
- **Graceful Failures**: Proper error messages and cleanup on failure
- **Resource Cleanup**: Git repositories cleaned up after use

## Logging

Logs are written to both console and file:

- Location: `<logFileDir>/CICD_<timestamp>.log`
- Format: `YYYY-MM-DD HH:MM:SS - LEVEL - [function:line] - message`
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Security Considerations

⚠️ **Important Security Notes**:

1. **Credentials**: Never commit configuration files with credentials to version control
2. **Use Environment Variables**: Consider using environment variables for sensitive data
3. **Git Tokens**: Use personal access tokens with minimal required permissions
4. **Rotate Credentials**: Regularly rotate passwords and tokens
5. **Audit Logs**: Review logs for sensitive information before sharing

## Configuration Constants

Edit `config.py` to customize:

- `API_TIMEOUT`: API request timeout (default: 30s)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `RETRY_BACKOFF_FACTOR`: Retry delay multiplier (default: 2)
- `PULL_STATUS_CHECK_INTERVAL`: Pull status check interval (default: 15s)
- `TAG_BATCH_SIZE`: Assets per tagging batch (default: 100)

## Troubleshooting

### Common Issues

**"No assets found with specified tags"**
- Verify tags exist in source environment
- Check project name matches exactly
- Ensure user has permissions to view assets

**"Authentication failed"**
- Verify credentials are correct
- Check region is correct (e.g., 'dm-us', 'dm-eu')
- Ensure account is not locked

**"Git operation failed"**
- Verify Git repository URL is accessible
- Check Git credentials/token is valid
- Ensure branches exist

**"Pull operation failed"**
- Check commit hash is valid
- Verify assets exist in Git at that commit
- Ensure target environment has space/permissions

### Slack Bot Issues

**Bot doesn't respond**
- Check Slack tokens in `.env`
- Verify Socket Mode is enabled in Slack app
- Check console for connection errors

**"Config file not found"**
- Provide full path or place file in project folder
- Use relative path from project directory

**Migration fails at specific step**
- Check real-time updates for error details
- Review log file in configured `logFileDir`
- Verify credentials and permissions
- Check network connectivity to IICS and Git

## Architecture

### Module Structure

```
agent.py                    # Main: Slack bot with Claude Sonnet 4
└── CICD/                   # CICD automation package
    ├── main.py             # Orchestration and workflow
    ├── logger.py           # Logging configuration
    ├── login.py            # IICS authentication
    ├── taggedAssets.py     # Asset retrieval
    ├── cherrypick.py       # Git operations
    ├── createProjectsAndFolders.py  # Target structure setup
    ├── pull.py             # Asset import
    ├── postMigrationTag.py # Post-migration tagging
    ├── database.py         # Audit logging
    ├── config.py           # Configuration constants
    └── utils.py            # Utility functions
```

### Slack Bot Architecture

```
User (Slack)
    ↓
Slack Bolt Handler
    ↓
LangChain ReAct Agent (Claude Sonnet 4)
    ↓
run_cicd_migration Tool
    ↓
┌─────────────────────────────────────┐
│ 1. Load/Validate Config             │
│ 2. Ask for Missing Fields (1-by-1)  │
│ 3. Update JSON File                 │
│ 4. Show Config & Confirm            │
│ 5. Run 8-Step Migration             │
│    └─> Real-time Slack Updates      │
│ 6. Store Last Config in Session     │
└─────────────────────────────────────┘
```

## Database Schema

The tool optionally logs to a database table:

```sql
CREATE TABLE dbo.Deployment_Details (
    ProjectName VARCHAR(255),
    IICSSourceOrg VARCHAR(255),
    IICSSourceOrgID VARCHAR(255),
    CommitHash VARCHAR(255),
    Tag VARCHAR(255),
    Deployment_Date DATE,
    Rollback_Date DATE,
    IICSTargetOrgID VARCHAR(255),
    IICSTargetOrg VARCHAR(255),
    AssetsMigrated INT
);
```

## Contributing

When contributing, ensure:

1. Follow existing code style (snake_case, type hints)
2. Add comprehensive error handling
3. Update documentation
4. Test with various asset types
5. Never commit credentials

## License

Internal use only - contact your organization for usage terms.

## IDMC Query API Reference

### Query Filters

The bot supports powerful query filters for searching assets:

**By Type:**
```
get objects with type DTEMPLATE        # All mappings
get objects with type MTT              # All mapping tasks
get objects with type CONNECTION       # All connections
```

**By Tag:**
```
list assets with tag Production        # Assets tagged "Production"
get objects with tag Dev               # Assets tagged "Dev"
```

**By Path:**
```
get objects in folder Project/Folder   # Assets in specific folder
list assets in Munich_Demo/Test        # Assets in nested folder
```

**Combined Filters:**
```
type=='MTT' and tags contains 'Production'
path=='Project/Test' and type=='DTEMPLATE'
name contains 'Customer' and tags contains 'Active'
```

### Asset Type Reference

| Type | Description | Can Tag? |
|------|-------------|----------|
| `DTEMPLATE` | Mapping | ✅ Yes |
| `MTT` | Mapping Task | ✅ Yes |
| `DSS` | Synchronization Task | ✅ Yes |
| `CONNECTION` | Connection | ✅ Yes |
| `AI_CONNECTION` | Application Connection | ✅ Yes |
| `AI_SERVICE_CONNECTOR` | Service Connector | ✅ Yes |
| `PROCESS` | Process | ✅ Yes |
| `TASKFLOW` | Taskflow | ✅ Yes |
| `SCHEDULE` | Schedule | ✅ Yes |
| `PROJECT` | Project | ❌ No |
| `FOLDER` | Folder | ❌ No |

### Example Workflows

**1. Find and Tag Test Assets:**
```
You: list all mappings in folder Test_Project/Dev
Bot: [Shows 20 mappings]

You: tag the first 5 with "ReadyForQA"
Bot: ✅ Successfully tagged 5 asset(s)!

You: how many assets have tag ReadyForQA now?
Bot: 📊 Total count: 5 items
```

**2. Audit Production Assets:**
```
You: give me count of assets with tag Production
Bot: 📊 Total count: 156 items

You: list all mapping tasks with tag Production
Bot: [Generates Excel with filtered results]
```

**3. Bulk Operations:**
```
You: get all connections in project DataHub
Bot: [Shows connections]

You: tag all of them with "Validated"
Bot: ✅ Successfully tagged 12 asset(s)!
```

## Support

For issues or questions:
1. Check **[SETUP_GUIDE.md](SETUP_GUIDE.md)** for installation troubleshooting
2. Review logs in `Logs/` directory for detailed error messages
3. Check error messages for specific guidance
4. Contact your IICS administrator for environment-specific issues
5. Check Slack bot console output for agent-related issues

## Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup from scratch
- **[README.md](README.md)** - This file, features and usage
- **Logs/** - Runtime logs for debugging
