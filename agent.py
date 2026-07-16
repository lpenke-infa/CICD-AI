import os
import json
import tempfile
import logging
import httpx
import requests
from typing import Dict, Any
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

# Import tool modules
from tools import (
    cicd_migration_tool,
    execute_cicd_migration,
    pre_migration_check_tool,
    execute_pre_migration_check,
    post_migration_check_tool,
    execute_post_migration_check,
    idmc_operations_tool,
    execute_idmc_operation
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Words that count as an affirmative reply to a pending confirmation prompt.
AFFIRMATIVE_REPLIES = {'yes', 'y', 'proceed', 'continue', 'yeah', 'yep', 'ok', 'okay', 'sure'}

# Maximum number of stored conversation messages to keep per conversation.
# History is stored as alternating (HumanMessage, AIMessage) pairs, so this is
# an even number (~100 turns). Well within the model's context window.
MAX_HISTORY_MESSAGES = 200

# Generic message shown to the user when something goes wrong. Full exception
# detail is written to the logs, never surfaced to Slack, so we don't leak
# internal paths, credentials, or stack information to end users.
GENERIC_ERROR_MESSAGE = (
    "❌ Sorry, something went wrong while processing your request. "
    "Please try again, and if the problem persists contact your administrator."
)


def _is_affirmative(user_input: str) -> bool:
    """Return True if the user's message is an affirmative confirmation."""
    return user_input.lower().strip() in AFFIRMATIVE_REPLIES


def _is_proceed_anyway(user_input: str) -> bool:
    """
    Return True if the user explicitly acknowledged proceeding despite issues.

    Requires the words 'proceed' or 'anyway' (not just a plain 'yes'), so a
    migration with known invalid/checked-out assets needs a deliberate override.
    """
    text = user_input.lower().strip()
    return 'proceed anyway' in text or 'anyway' in text or 'proceed' in text


# Maps an operation to its log file (all live in the 'Logs' directory).
_OPERATION_LOG_FILES = {
    'cicd': 'CICDMigration.log',
    'migration': 'CICDMigration.log',
    'pre': 'PreMigrationCheck.log',
    'pre_migration': 'PreMigrationCheck.log',
    'post': 'PostMigrationCheck.log',
    'post_migration': 'PostMigrationCheck.log',
    'idmc': 'IDMCFunctionalities.log',
}


@tool
def read_operation_logs(operation: str, max_lines: int = 80) -> str:
    """
    Read the most recent log lines for an operation to explain what happened
    (e.g. why a migration or check failed). Use this when the user asks why
    something failed, what the error was, or for details about a past run.

    Args:
        operation: Which operation's log to read. One of:
                   'cicd' / 'migration'  -> CI/CD Migration log
                   'pre' / 'pre_migration' -> Pre-Migration Check log
                   'post' / 'post_migration' -> Post-Migration Check log
                   'idmc' -> IDMC Operations log
        max_lines: How many of the most recent log lines to return (default 80,
                   capped at 300).

    Returns:
        The tail of the relevant log file as plain text, or a message if the
        log cannot be found.
    """
    key = (operation or '').strip().lower()
    log_filename = _OPERATION_LOG_FILES.get(key)

    if not log_filename:
        valid = ', '.join(sorted(set(_OPERATION_LOG_FILES.keys())))
        return f"Unknown operation '{operation}'. Valid values: {valid}."

    log_path = os.path.join(os.path.dirname(__file__), 'Logs', log_filename)

    if not os.path.exists(log_path):
        return f"No log file found for '{operation}' (expected {log_filename}). The operation may not have run yet."

    try:
        max_lines = max(1, min(int(max_lines), 300))
    except (TypeError, ValueError):
        max_lines = 80

    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        tail = lines[-max_lines:]
        return (
            f"Last {len(tail)} line(s) of {log_filename}:\n\n"
            + "".join(tail)
        )
    except Exception as e:
        logger.error(f"Failed to read log {log_path}: {str(e)}", exc_info=True)
        return f"Could not read the {operation} log file."


@tool
def save_config_file(filename: str, config_data: dict) -> str:
    r"""
    Save CI/CD configuration to a JSON file in the default configs directory.

    Args:
        filename: Name of the config file (e.g., 'test_cicd.json')
        config_data: Dictionary containing the configuration data

    Returns:
        A confirmation message containing the saved config path and a prompt
        asking the user which operation to run.
    """
    # Use relative path from project root
    default_path = os.path.join(os.path.dirname(__file__), "Configs")

    if not filename.endswith('.json'):
        filename += '.json'

    file_path = os.path.join(default_path, filename)

    try:
        os.makedirs(default_path, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)

        return f"✅ Configuration saved successfully to: `{file_path}`"

    except Exception as e:
        logger.error(f"Failed to save configuration to {file_path}: {str(e)}", exc_info=True)
        return "❌ Failed to save configuration. Please check the file name and try again."


@tool
def update_config_file(filename: str, updates: dict) -> str:
    r"""
    Update specific fields in an existing config file WITHOUT rewriting the whole
    file. Reads the current file, changes only the keys given in `updates`, and
    keeps every other field exactly as-is.

    Use this whenever the user wants to change one or a few fields in a config
    that already exists (e.g. "change PreMigration_Tag to X", "update the target
    region"). Do NOT use save_config_file for edits - that requires resupplying
    every field. Only ask the user for the values that are actually changing.

    Args:
        filename: Name of the existing config file (e.g., 'demo_migration.json')
        updates: Dictionary of ONLY the fields to change (e.g.,
                 {"PreMigration_Tag": ["CICD_DEMO_TEST"]}). All other fields in
                 the file are preserved.

    Returns:
        A confirmation message listing what changed, or an error if the file
        doesn't exist.
    """
    default_path = os.path.join(os.path.dirname(__file__), "Configs")

    if not filename.endswith('.json'):
        filename += '.json'

    file_path = os.path.join(default_path, filename)

    if not os.path.exists(file_path):
        return (
            f"❌ Config file `{filename}` not found in Configs/. "
            f"Use save_config_file to create a new one, or check the filename."
        )

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Merge only the provided keys; everything else is untouched.
        changed = []
        for key, new_value in updates.items():
            old_value = config.get(key, '<not set>')
            config[key] = new_value
            changed.append(f"• `{key}`: `{old_value}` → `{new_value}`")

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        changes_text = "\n".join(changed) if changed else "• (no fields specified)"
        return f"""✅ Updated `{filename}` (other fields preserved):
{changes_text}"""

    except json.JSONDecodeError as e:
        logger.error(f"Config file {file_path} is not valid JSON: {str(e)}")
        return f"❌ Could not update `{filename}` - the file is not valid JSON."
    except Exception as e:
        logger.error(f"Failed to update configuration {file_path}: {str(e)}", exc_info=True)
        return f"❌ Failed to update `{filename}`. Please try again."


SYSTEM_PROMPT = """
You are an IICS CI/CD Migration Assistant.

You execute four operations:
1. Pre-Migration Check - validate assets before migration
2. CI/CD Migration - migrate assets between environments
3. Post-Migration Check - validate after migration
4. IDMC Operations - query/manage IICS assets

You NEVER:
- Fabricate information
- Guess missing config values
- Claim operations succeeded when they failed

====================================================================

INTENT DETECTION:

Match user request to ONE of these:
- "hi" / "hello" / "help" → Show Welcome Menu
- "run pre-migration" / "validate assets" → Pre-Migration Check
- "run migration" / "migrate" / "cicd" → CI/CD Migration
- "post-migration" / "validate migration" → Post-Migration Check
- "list assets" / "tag assets" / "create project" → IDMC Operations
- Cannot determine → Show Welcome Menu

After showing Welcome Menu, DO NOT show it again in same conversation.

CONFIGURATION INPUT:
1. File uploaded → Parse file, ask which operation
2. File name mentioned ("use demo.json") → Use that file, ask which operation
3. Interactive chat ("I want to migrate from dev to qa") → Collect missing values, then execute
4. Operation already clear → Execute immediately with available config

EDITING AN EXISTING CONFIG FILE:
When the user wants to CHANGE a field in a config file that already exists
(e.g. "change PreMigration_Tag to X", "update the region in demo.json"), use the
update_config_file tool with ONLY the fields that change. It preserves all other
fields automatically.
- DO NOT use save_config_file for edits (it overwrites the whole file and needs
  every field re-supplied).
- DO NOT ask the user to re-provide unchanged fields (credentials, git config,
  project name, etc.) — update_config_file keeps them. Only ask for the new
  value(s) being changed.
Example: user says "update PreMigration_Tag to CICD_DEMO_TEST in demo.json"
→ call update_config_file(filename="demo.json", updates={"PreMigration_Tag": ["CICD_DEMO_TEST"]})

====================================================================

OPERATIONS:

1. Pre-Migration Check
   Tool: pre_migration_check_tool
   Needs: source credentials, target credentials, pre-migration tags, project name
   Does: Validates assets exist, generates Excel report

2. CI/CD Migration
   Tool: cicd_migration_tool
   Needs: source/target credentials, git config, pre/post tags, project name
   Does: 8-step migration with real-time updates

3. Post-Migration Check
   Tool: post_migration_check_tool
   Needs: target credentials, post-migration tags, project name
   Does: Validates migrated assets, generates Excel report

4. IDMC Operations
   Tool: idmc_operations_tool
   Needs: credentials, operation name, parameters
   Examples: "list assets with tag X", "create project Y", "tag asset Z"

====================================================================

CONFIGURATION COLLECTION:

Three ways to get config:
1. User uploads file → Parse it
2. User mentions file name ("use demo.json") → Load from Configs/
3. User provides values in chat → Collect interactively

Interactive collection rules:
- Ask ONE question at a time
- Ask ONLY for missing required fields
- NEVER guess or assume values
- Confirm all values before executing

Required fields by operation (use these EXACT key names):

- Pre-Migration:
  ProjectName,
  IICS_SRC_username, IICS_SRC_password, IICS_SRC_region,
  IICS_TGT_username, IICS_TGT_password, IICS_TGT_region,
  PreMigration_Tag (array, one or more tags)

- CI/CD Migration (all Pre-Migration fields, plus):
  PostMigration_Tag (array with EXACTLY ONE tag),
  Git_Repository_URL (must start with https://),
  Git_config_useremail (valid email),
  Git_config_username,
  Git_password (git token),
  Git_SRC_Branch, Git_TGT_Branch (must differ),
  Publish (integer, 0 or 1)

- Post-Migration:
  ProjectName,
  IICS_TGT_username, IICS_TGT_password, IICS_TGT_region,
  PostMigration_Tag (array with EXACTLY ONE tag)

====================================================================

FILE UPLOAD HANDLING:

When user uploads a file:

1. Parse the file content (supports: JSON, YAML, TXT, CSV, INI, etc.)

2. Extract and map config values intelligently:
   - Map "username" → "IICS_SRC_username" (smart mapping OK)
   - Map "region" → "IICS_SRC_region"
   - Map "password" → "IICS_SRC_password"
   - DO NOT invent values that aren't in the file
   - If ambiguous (e.g., one "username" but need SRC and TGT), ask which is which

3. Call save_config_file tool with extracted values

4. Ask which operation to run:
   "Which operation? 1) Pre-Migration 2) Migration 3) Post-Migration 4) IDMC"

5. Check for missing required fields
   - If missing → Ask user for those specific fields
   - If complete → Execute operation immediately

Example:
File has: project="MyProject", user="admin@test.com", tag="PreMig"
Maps to: ProjectName="MyProject", IICS_SRC_username="admin@test.com", PreMigration_Tag=["PreMig"]
Missing: IICS_SRC_password, IICS_SRC_region
Ask: "I need IICS_SRC_password and IICS_SRC_region. What are they?"

====================================================================

TAGGING RESTRICTIONS:

PROJECT and FOLDER types CANNOT be tagged in IICS.

Taggable types:
DTEMPLATE, MTT, DSS, DTT, DMASK, DRS, DMAPPLET, CONNECTION, AGENT, AGENTGROUP,
BSERVICE, HSCHEMA, PCS, FWCONFIG, CUSTOMSOURCE, MI_FILE_LISTENER, MI_TASK,
DBMI_TASK, APPMI_TASK, WORKFLOW, SCHEDULE, TASKFLOW, UDF, PROCESS, GUIDE,
AI_CONNECTION, AI_SERVICE_CONNECTOR, PROCESS_OBJECT, CLEANSE, DEDUPLICATE,
DICTIONARY, PARSE, RULE_SPECIFICATION, VERIFIER, LABELER, STRUCTURE_DISCOVERY

Before calling tag_assets or untag_assets:
1. Filter out any assets where type='PROJECT' or type='FOLDER'
2. If any were filtered, tell user: "Skipped X PROJECT/FOLDER assets (cannot be tagged)"
3. Only tag the remaining supported types

====================================================================

COUNT vs LIST QUERIES:

The is_count_query parameter ONLY applies to the list/retrieve operations:
get_objects, get_users, get_agents, get_schedules, get_runtime_environments.
It has no effect on create/update/delete operations, so leave it False for those.

For a list/retrieve operation, set is_count_query:

is_count_query=True (only return count, no Excel report):
- "how many", "count", "total", "number of"
- Examples: "How many mappings?", "Count projects", "Total users"

is_count_query=False (return full list with Excel report):
- "list", "show", "get", "display", "report"
- Examples: "List all mappings", "Show projects", "Get users"

====================================================================

CONVERSATION FLOW:

1. User provides input → Identify what you have and what's missing
2. Ask for missing fields ONE at a time
3. After collecting all required fields → Confirm with user
4. User confirms → Execute tool immediately
5. Tool running → Show progress updates from tool
6. Tool completes → Report result (success/failure/warnings)

Context memory:
- Remember values from current conversation
- Reuse: ProjectName, usernames, regions, tags, file paths
- DO NOT assume values user hasn't provided
- If unsure value is still valid, ask: "Still using ProjectName 'X'?"

Example flows:
A) User: "Run migration"
   You: "How do you want to provide config? 1) Upload file 2) Use existing file 3) Enter values"

B) User: "Run migration with demo.json"
   You: "Starting migration with Configs/demo.json..." [call tool]

C) User: [uploads file]
   You: "File parsed. Which operation? 1) Pre-Migration 2) Migration..."

====================================================================

CONTEXT MEMORY:

Remember from current conversation:
- ProjectName, usernames, regions, tags
- Config file paths
- Organization names (from tool responses)
- Asset IDs, folder paths

Reuse when user says "that", "same", "it":
- "List assets with that tag" → Use last mentioned tag
- "Use the same project" → Use last ProjectName
- "Tag it" → Use last mentioned asset ID

DO NOT reuse across different operations:
- Pre-Migration used "dev" region → Don't assume Migration uses "dev"
- Tagged assets with "TAG1" → Don't assume next tagging uses "TAG1"
- Always confirm when switching operations

Example:
User: "List mappings with tag PreMig"
You: [executes, shows results]
User: "Now list connections with that tag"
You: [uses "PreMig" automatically]

====================================================================

TOOL EXECUTION:

Always call tools, never describe what you'll do.

Tool call rules:
1. User confirms → Call tool immediately
2. Tool running → Wait for completion, show progress updates
3. Tool completes → Report exact result (don't embellish)
4. Tool fails → Show error, suggest fix, DO NOT claim success

File uploaded workflow:
1. Parse file → call save_config_file
2. Ask which operation
3. Check for missing required fields
4. If missing → Ask for them
5. If complete → Call operation tool

"Yes" confirmation workflow:
User says "yes" after config saved:
1. Find saved config file path from conversation
2. Check required fields exist (use the "Required fields by operation" list above)
3. If missing → Ask: "I need [field]. What is it?"
4. If complete → Call tool with config_file_path
5. DO NOT repeat "config saved" message

Never:
- Fabricate tool results
- Claim success if tool failed
- Call tool with incomplete config

====================================================================

EXPLAINING FAILURES / READING LOGS:

When the user asks why an operation failed, what the error was, or for more
detail about a past run (e.g. "why did the pull fail?", "what went wrong?",
"check the logs"), call the read_operation_logs tool with the relevant
operation ('cicd', 'pre', 'post', or 'idmc'). Then explain the specific cause
from the log. NEVER say you cannot read logs - you have the read_operation_logs
tool for exactly this. Do not give generic guesses when the log has the answer.

====================================================================

UNSUPPORTED REQUESTS:

If user asks for something you cannot do:
1. Say: "I can't do [that]. I can only handle Pre-Migration, Migration, Post-Migration, and IDMC operations."
2. Show Welcome Menu
3. DO NOT invent features or pretend you can do it
4. DO NOT suggest workarounds you can't actually execute

Examples of unsupported:
- "Deploy to production server" → Not supported
- "Run SQL query" → Not supported
- "Backup database" → Not supported

====================================================================

SLACK FORMATTING:

Bold: *text* (single asterisk, NOT **text**)
Italic: _text_
Code: `text`
Emoji: :emoji_name:
Lists: 1., 2., 3. or • bullet

Keep responses:
- Concise (2-3 sentences when possible)
- Professional (no casual slang)
- Actionable (tell user what to do next)

====================================================================

WELCOME MENU:

When showing menu, use this exact format:

👋 *Welcome to the IICS CI/CD Migration Assistant!*

I can help you with:

1. *Pre-Migration Check*
   Validate assets before migration

2. *CI/CD Migration*
   Migrate assets from source to target environment

3. *Post-Migration Check*
   Validate migrated assets

4. *IDMC Operations* _(Development - In Progress)_
   Query/manage assets, tags, projects, folders, schedules, users

What would you like to do? (Reply with number or description)
"""

class Agent:
    """
    Refactored CI/CD and IDMC Automation Agent with Slack integration.

    This class focuses solely on:
    1. Slack message handling
    2. LLM interaction for intent understanding
    3. Routing to appropriate tool modules
    4. Managing conversation context

    All business logic is delegated to tool modules.
    """

    def __init__(self):
        """Initialize the agent with Slack and Claude LLM clients."""
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")
        self.anthropic_base_url = os.getenv("ANTHROPIC_BEDROCK_BASE_URL")
        self.anthropic_auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")

        if not all([self.slack_bot_token, self.slack_app_token,
                   self.anthropic_base_url, self.anthropic_auth_token]):
            raise ValueError("Missing required environment variables in .env file")

        self.app = App(token=self.slack_bot_token)

        # Bind all available tools to the LLM
        self.llm = ChatOpenAI(
            model="claude-opus-4-8",
            api_key=self.anthropic_auth_token,
            base_url=self.anthropic_base_url + "/v1",
            http_client=httpx.Client(verify=False)
        ).bind_tools([
            save_config_file,
            update_config_file,
            pre_migration_check_tool,
            cicd_migration_tool,
            post_migration_check_tool,
            idmc_operations_tool,
            read_operation_logs
        ])

        self.conversation_history = {}
        self.last_migration_config = {}  # For Post-Migration confirmation
        self.last_pre_migration_config = {}  # For CICD Migration confirmation

        self._register_handlers()

        logger.info("✅ Agent initialized successfully")

    def _register_handlers(self):
        """Register Slack event handlers for both mentions and direct messages."""

        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle when bot is mentioned in a channel."""
            self.handle_slack_message(event, say)

        @self.app.event("message")
        def handle_dm(event, say):
            """Handle direct messages to the bot."""
            # Handle both regular messages and file uploads
            if event.get("channel_type") == "im":
                # Skip bot messages and message changes
                if event.get("subtype") not in [None, "file_share"]:
                    return
                self.handle_slack_message(event, say)

    def handle_file_in_message(self, files: list, say, user_id: str, channel_id: str):
        """
        Handle file attachments in messages - accepts any file type.
        AI will read and understand the content to map values into JSON config.

        Args:
            files: List of file objects from Slack message
            say: Slack say function to send responses
            user_id: User ID who sent the file
            channel_id: Channel ID
        """
        try:
            # Create conversation key
            conversation_key = f"{channel_id}_{user_id}"

            for file_obj in files:
                filename = file_obj.get("name", "uploaded_file")
                download_url = file_obj.get("url_private_download")
                filetype = file_obj.get("filetype", "unknown")

                logger.info(f"📎 Processing file: {filename} (type: {filetype}) from user {user_id}")

                # Send immediate acknowledgment
                say(f"📎 _Received file: `{filename}` - analyzing..._")

                # Download the file
                headers = {"Authorization": f"Bearer {self.slack_bot_token}"}
                response = requests.get(download_url, headers=headers)

                if response.status_code != 200:
                    say(f"❌ Failed to download file: `{filename}`")
                    logger.error(f"Download failed with status {response.status_code}")
                    continue

                # Read file content based on type
                try:
                    # Try to decode as text first
                    file_content = response.content.decode('utf-8')

                    # If it's already JSON, save it directly
                    if filename.endswith('.json'):
                        try:
                            json_content = json.loads(file_content)
                            configs_dir = os.path.join(os.path.dirname(__file__), "Configs")
                            os.makedirs(configs_dir, exist_ok=True)
                            file_path = os.path.join(configs_dir, filename)

                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(json_content, f, indent=2)

                            say(f"✅ Configuration file saved: `{filename}`\n\n*What would you like to do?*\n1️⃣ Run pre-migration check\n2️⃣ Run CI/CD migration\n3️⃣ Run post-migration validation\n4️⃣ Just keep it for later")

                            logger.info(f"✅ Saved JSON config file: {file_path}")
                            continue

                        except json.JSONDecodeError:
                            pass  # Not valid JSON, let AI parse it

                    # For non-JSON files, let AI understand and map the content
                    say(f"📄 Analyzing file: `{filename}`...\n_Let me understand the content and map it to a configuration._")

                    # Initialize conversation history if needed
                    # (prior turns are supplied to the model via chat_history in
                    # _get_claude_response, so no separate context block is needed here)
                    if conversation_key not in self.conversation_history:
                        self.conversation_history[conversation_key] = []

                    # Prepare prompt for AI to parse the file
                    parse_prompt = f"""The user uploaded a configuration file with the following content:

```
{file_content}
```

Parse it and follow the FILE UPLOAD HANDLING steps in your system instructions
(map values -> call save_config_file -> ask which operation -> check missing fields).

Mapping notes for this file:
1. Extract all key-value pairs and map them into the standard config schema
   (IICS_SRC_*, IICS_TGT_*, Git_*, ProjectName, PreMigration_Tag, PostMigration_Tag, Publish, etc.).
2. Smart-map generic keys (e.g. "username" -> "IICS_SRC_username", "region" -> "IICS_SRC_region",
   "password" -> "IICS_SRC_password"). If a key is ambiguous (e.g. one "username" but both SRC and
   TGT are needed), ask which is which.
3. Convert tag values into arrays (e.g. "PreMig" -> ["PreMig"]).
4. Do NOT invent or assume values that aren't present in the file.

Then call save_config_file with:
- filename: "<tool-name>_config.json"
- config_data: all extracted key-value pairs, plus logFileDir = "Logs" and reportFileDir = "Reports".

After saving, ask which operation to run (per your system instructions), then check for any
missing required fields for that operation before executing.
"""
                    # Get AI response to parse the file
                    response_text, already_streamed = self._get_claude_response(
                        conversation_key,
                        parse_prompt,
                        say_callback=say,
                        channel_id=channel_id
                    )

                    # Send the response back to user only if it wasn't already
                    # streamed via say_callback (e.g. save_config_file message,
                    # or a follow-up question when the tool wasn't called)
                    if response_text and not already_streamed:
                        say(response_text)

                    logger.info(f"✅ AI processed file: {filename}")

                except UnicodeDecodeError:
                    say(f"❌ Unable to read file `{filename}` - it appears to be a binary file.\n\nPlease upload text-based configuration files (txt, json, yaml, csv, etc.)")
                    logger.error(f"Binary file detected: {filename}")
                    continue

        except Exception as e:
            logger.error(f"❌ Error handling file in message: {str(e)}", exc_info=True)
            say(GENERIC_ERROR_MESSAGE)

    def handle_slack_message(self, event: Dict[str, Any], say):
        """
        Unified handler for both mentions and direct messages.

        Args:
            event: Slack event data
            say: Slack say function to send responses
        """
        try:
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")

            # Check if message contains file attachments
            files = event.get("files", [])
            if files:
                logger.info(f"📎 File(s) detected in message from user {user_id}")
                self.handle_file_in_message(files, say, user_id, channel_id)
                return

            # Clean up mention tags if present
            if "<@" in text:
                text = text.split(">", 1)[-1].strip()

            if not text:
                return

            logger.info(f"📩 Received message from user {user_id} in channel {channel_id}")

            # Create unique conversation key for context
            conversation_key = f"{channel_id}_{user_id}"

            # Initialize conversation history if needed
            if conversation_key not in self.conversation_history:
                self.conversation_history[conversation_key] = []

            # Send immediate acknowledgment so user knows bot is working
            # Use Slack's typing indicator alternative - quick response
            say("⏳ _Processing your request..._")

            # Get Claude response using agent (pass channel_id for file uploads)
            response, already_streamed = self._get_claude_response(conversation_key, text, say, channel_id)

            # Keep only the most recent messages for context. Trim on a turn
            # boundary: if the slice would start on an AIMessage (an orphaned
            # reply whose HumanMessage got cut), drop it so history always begins
            # with a HumanMessage. This keeps each AI reply paired with the user
            # turn that produced it (some AI messages carry operation outcomes).
            history = self.conversation_history[conversation_key]
            if len(history) > MAX_HISTORY_MESSAGES:
                trimmed = history[-MAX_HISTORY_MESSAGES:]
                if trimmed and isinstance(trimmed[0], AIMessage):
                    trimmed = trimmed[1:]
                self.conversation_history[conversation_key] = trimmed

            # Send response to Slack only if it wasn't already streamed via say_callback
            if response and not already_streamed:
                say(response)

            logger.info(f"✅ Sent response to user {user_id}")

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}", exc_info=True)
            say(GENERIC_ERROR_MESSAGE)

    def _get_claude_response(self, conversation_key: str, user_input: str, say_callback=None, channel_id=None) -> tuple:
        """
        Get response from Claude AI and route to appropriate tool.

        Args:
            conversation_key: Unique key for conversation context
            user_input: User's message
            say_callback: Slack say function for real-time updates
            channel_id: Slack channel ID for file uploads

        Returns:
            Tuple of (response_text, already_streamed). When already_streamed is
            True the text was already sent to the user via say_callback (tool
            progress updates), so the caller must NOT send it again.
        """
        try:
            chat_history = self.conversation_history[conversation_key]

            # Always prepend the system prompt so the assistant stays anchored to
            # its role/instructions on EVERY turn (not just the first). Without
            # this, follow-up turns lost the system prompt and the model reverted
            # to generic-assistant behavior (e.g. denying it ran a migration).
            messages = [SystemMessage(content=SYSTEM_PROMPT)]
            messages.extend(chat_history)
            messages.append(HumanMessage(content=user_input))

            # Check for a pending confirmation prompt. These handlers stream all
            # output via say_callback, so mark already_streamed.
            #
            # A completed migration (last_migration_config) takes precedence over
            # a completed pre-migration check (last_pre_migration_config): the
            # migration handler clears the pre-migration entry, so if both are set
            # the migration one is the more recent prompt awaiting a "yes".
            if _is_affirmative(user_input) or _is_proceed_anyway(user_input):
                if conversation_key in self.last_migration_config:
                    return self._handle_post_migration_confirmation(conversation_key, say_callback, channel_id), True
                if conversation_key in self.last_pre_migration_config:
                    pre_info = self.last_pre_migration_config[conversation_key]
                    # If the pre-check found blocking-class issues, a plain "yes"
                    # is not enough - require an explicit "proceed anyway" so the
                    # user can't accidentally migrate known-bad assets.
                    if pre_info.get('has_issues') and not _is_proceed_anyway(user_input):
                        return (
                            "⚠️ The pre-migration check found issues (invalid or checked-out assets) "
                            "that may cause the migration to fail.\n\n"
                            "If you understand the risk and still want to migrate, reply "
                            "\"*yes, proceed anyway*\".",
                            False
                        )
                    return self._handle_cicd_migration_confirmation(conversation_key, say_callback, channel_id), True

            # Get response from LLM
            response = self.llm.invoke(messages)

            # Check if tool calls are present
            if hasattr(response, 'tool_calls') and response.tool_calls:
                return self._handle_tool_calls(response.tool_calls, conversation_key, user_input, say_callback, channel_id)

            # No tool call, just return the response (not yet shown to the user)
            response_text = response.content

            # Update conversation history
            self.conversation_history[conversation_key].append(HumanMessage(content=user_input))
            self.conversation_history[conversation_key].append(AIMessage(content=response_text))

            return response_text, False

        except Exception as e:
            logger.error(f"❌ Error getting Claude response: {str(e)}", exc_info=True)
            return GENERIC_ERROR_MESSAGE, False

    def _handle_tool_calls(self, tool_calls, conversation_key, user_input, say_callback, channel_id):
        """
        Route tool calls to appropriate execution functions.

        Args:
            tool_calls: List of tool calls from LLM
            conversation_key: Conversation context key
            user_input: User's input message
            say_callback: Slack callback for updates
            channel_id: Slack channel for file uploads

        Returns:
            Tuple of (result_message, already_streamed). Operation tools stream
            their output via say_callback (already_streamed=True); save_config_file
            does not, so its message must be sent by the caller (already_streamed=False).
        """
        # Required arguments per tool - guard against the model calling a tool
        # without them so we return a clear message instead of raising KeyError.
        required_args = {
            'cicd_migration_tool': ['config_file_path'],
            'pre_migration_check_tool': ['config_file_path'],
            'post_migration_check_tool': ['config_file_path'],
            'idmc_operations_tool': ['username', 'password', 'region', 'operation', 'parameters'],
            'save_config_file': ['filename', 'config_data'],
            'update_config_file': ['filename', 'updates'],
        }

        for tool_call in tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']

            missing = [a for a in required_args.get(tool_name, []) if a not in tool_args]
            if missing:
                logger.error(f"Tool '{tool_name}' called without required args: {missing}")
                return (
                    f"❌ I couldn't run `{tool_name}` because these values are missing: "
                    f"{', '.join(missing)}. Please provide them and try again.",
                    False
                )

            # Route to CICD Migration Tool
            if tool_name == 'cicd_migration_tool':
                result = execute_cicd_migration(
                    config_file_path=tool_args['config_file_path'],
                    say_callback=say_callback
                )

                # Store migration config for post-migration validation
                if isinstance(result, dict) and result.get('migration_completed'):
                    self.last_migration_config[conversation_key] = result

                self._update_conversation_history(
                    conversation_key, user_input, result,
                    operation=f"CI/CD Migration (config: {tool_args['config_file_path']})"
                )
                return self._format_result(result), True

            # Route to Pre-Migration Check Tool
            elif tool_name == 'pre_migration_check_tool':
                result = execute_pre_migration_check(
                    config_file_path=tool_args['config_file_path'],
                    say_callback=say_callback
                )

                # Upload report if available
                if result.get('success') and result.get('report_path') and channel_id:
                    self._upload_report(result['report_path'], channel_id, say_callback)

                # Store pre-migration config for CICD migration prompt. Record
                # whether blocking-class issues were found so the confirmation
                # gate can require a stronger "proceed anyway" acknowledgment.
                if isinstance(result, dict) and result.get('success'):
                    self.last_pre_migration_config[conversation_key] = {
                        'config_file_path': tool_args['config_file_path'],
                        'has_issues': result.get('has_issues', False)
                    }

                self._update_conversation_history(
                    conversation_key, user_input, result,
                    operation=f"Pre-Migration Check (config: {tool_args['config_file_path']})"
                )
                return self._format_result(result), True

            # Route to Post-Migration Check Tool
            elif tool_name == 'post_migration_check_tool':
                result = execute_post_migration_check(
                    config_file_path=tool_args['config_file_path'],
                    say_callback=say_callback
                )

                # Upload report if available
                if result.get('success') and result.get('report_path') and channel_id:
                    self._upload_report(result['report_path'], channel_id, say_callback)

                self._update_conversation_history(
                    conversation_key, user_input, result,
                    operation=f"Post-Migration Check (config: {tool_args['config_file_path']})"
                )
                return self._format_result(result), True

            # Route to IDMC Operations Tool
            elif tool_name == 'idmc_operations_tool':
                parameters = json.loads(tool_args['parameters']) if isinstance(tool_args['parameters'], str) else tool_args['parameters']

                result = execute_idmc_operation(
                    username=tool_args['username'],
                    password=tool_args['password'],
                    region=tool_args['region'],
                    operation=tool_args['operation'],
                    parameters=parameters,
                    say_callback=say_callback,
                    is_count_query=tool_args.get('is_count_query', False)
                )

                # Upload report if Excel was generated
                if result.get('report_generated') and result.get('report_path') and channel_id:
                    self._upload_report(result['report_path'], channel_id, say_callback)

                self._update_conversation_history(
                    conversation_key, user_input, result,
                    operation=f"IDMC Operation: {tool_args['operation']}"
                )
                return self._format_result(result), True

            # Route to Save Config Tool. After saving, hand back to the model so
            # it can auto-continue to whatever operation the user already asked
            # for (rather than dead-ending on a fixed menu that loops).
            elif tool_name == 'save_config_file':
                tool_result = save_config_file.invoke(tool_args)
                filename = tool_args.get('filename', '')
                return self._continue_after_config_change(
                    conversation_key, user_input, tool_result, filename,
                    say_callback, channel_id
                )

            # Route to Update Config Tool - edits specific fields in place, then
            # continues to the requested operation the same way.
            elif tool_name == 'update_config_file':
                tool_result = update_config_file.invoke(tool_args)
                filename = tool_args.get('filename', '')
                return self._continue_after_config_change(
                    conversation_key, user_input, tool_result, filename,
                    say_callback, channel_id
                )

            # Route to Read Logs Tool - read the log, then ask the LLM to explain
            # it in plain language rather than dumping raw log lines to the user.
            elif tool_name == 'read_operation_logs':
                log_text = read_operation_logs.invoke(tool_args)

                explain_messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=(
                        f"The user asked: \"{user_input}\"\n\n"
                        f"Here are the relevant log lines:\n\n{log_text}\n\n"
                        "Explain in 2-4 sentences what happened - especially the "
                        "specific cause of any failure - using Slack formatting. "
                        "Base your answer only on these logs; do not invent details."
                    ))
                ]
                explanation = self.llm.invoke(explain_messages).content

                self._update_conversation_history(
                    conversation_key, user_input, explanation,
                    operation=f"Read logs: {tool_args.get('operation', 'unknown')}"
                )
                return explanation, False

        return "No matching tool found", False

    def _continue_after_config_change(self, conversation_key, user_input, tool_result,
                                      filename, say_callback, channel_id):
        """
        After a config file is saved or updated, decide the next action.

        Instead of dead-ending on a fixed "which operation?" menu (which loses the
        operation the user already asked for and causes a loop), record the config
        result and give the model one more turn with the full conversation. The
        model may then call an operation tool directly (auto-proceed to what the
        user already requested) or ask a clarifying question only if it's unclear.

        Returns:
            (message, already_streamed) tuple, matching _handle_tool_calls.
        """
        # Record the config change in history so the follow-up turn sees it.
        self._update_conversation_history(conversation_key, user_input, tool_result)

        # Send the save/update confirmation to the user now.
        if say_callback:
            say_callback(tool_result)

        # Follow-up turn: let the model act on the just-saved config using the
        # conversation so far. It sees the config path and the user's earlier
        # stated intent, and is told to auto-run that operation or ask only if
        # genuinely ambiguous.
        chat_history = self.conversation_history[conversation_key]
        follow_up = (
            f"The configuration file `{filename}` has just been saved/updated. "
            "Based on the conversation so far, determine which operation the user "
            "wants (Pre-Migration Check, CI/CD Migration, Post-Migration Check, or "
            "IDMC Operations). If the user has already indicated an operation, call "
            "that operation's tool now with this config file. Only if the intended "
            "operation is genuinely unclear should you ask - and then ask a short, "
            "specific question rather than re-listing all four options. Do NOT call "
            "save_config_file or update_config_file again."
        )
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        messages.extend(chat_history)
        messages.append(HumanMessage(content=follow_up))

        response = self.llm.invoke(messages)

        # If the model decided on an operation, run it via the normal routing.
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Guard against the model looping back into a config tool.
            op_calls = [
                tc for tc in response.tool_calls
                if tc['name'] not in ('save_config_file', 'update_config_file')
            ]
            if op_calls:
                return self._handle_tool_calls(
                    op_calls, conversation_key, user_input, say_callback, channel_id
                )

        # No operation chosen - the model asked a clarifying question. The
        # save/update confirmation was already sent via say_callback above; the
        # caller will send this clarify text (already_streamed=False).
        clarify = response.content or "Which operation would you like to run next?"
        self.conversation_history[conversation_key].append(AIMessage(content=clarify))
        return clarify, False

    def _handle_cicd_migration_confirmation(self, conversation_key, say_callback, channel_id):
        """
        Handle user confirmation for CICD migration after pre-migration check.

        Args:
            conversation_key: Conversation context key
            say_callback: Slack callback for updates
            channel_id: Slack channel for file uploads

        Returns:
            Result message from migration
        """
        pre_migration_info = self.last_pre_migration_config[conversation_key]
        config_file_path = pre_migration_info['config_file_path']

        # Execute CICD migration using the same config file
        result = execute_cicd_migration(
            config_file_path=config_file_path,
            say_callback=say_callback
        )

        # Store migration config for post-migration validation
        if isinstance(result, dict) and result.get('migration_completed'):
            self.last_migration_config[conversation_key] = result

        # Clear stored pre-migration config
        del self.last_pre_migration_config[conversation_key]

        # Update conversation history
        self._update_conversation_history(
            conversation_key, "yes", result,
            operation=f"CI/CD Migration (config: {config_file_path})"
        )

        return result.get('message', str(result))

    def _handle_post_migration_confirmation(self, conversation_key, say_callback, channel_id):
        """
        Handle user confirmation for post-migration validation.

        Args:
            conversation_key: Conversation context key
            say_callback: Slack callback for updates
            channel_id: Slack channel for file uploads

        Returns:
            Result message from validation
        """
        migration_info = self.last_migration_config[conversation_key]

        # Read migration details defensively - these are populated on the
        # success path of execute_cicd_migration, but guard against a partial
        # dict so a "yes" reply can never crash the handler.
        post_migration_tag = migration_info.get('post_migration_tag', [])
        if isinstance(post_migration_tag, str):
            post_migration_tag = [post_migration_tag]

        # Show config preview
        config_preview = f"""📋 *Post-Migration Validation Configuration:*

🎯 *Target Environment:*
   • Username: `{migration_info.get('target_username', 'N/A')}`
   • Password: `{'*' * 8}`
   • Region: `{migration_info.get('target_region', 'N/A')}`

📦 *Validation Details:*
   • Project: `{migration_info.get('project_name', 'N/A')}`
   • Tags to Check: `{', '.join(post_migration_tag) if post_migration_tag else 'N/A'}`

Proceeding with validation..."""

        if say_callback:
            say_callback(config_preview)

        # Create temp config file
        post_config = {
            "IICS_TGT_username": migration_info.get('target_username'),
            "IICS_TGT_password": migration_info.get('target_password'),
            "IICS_TGT_region": migration_info.get('target_region'),
            "PostMigration_Tag": post_migration_tag,
            "ProjectName": migration_info.get('project_name'),
            "logFileDir": "Logs",
            "reportFileDir": "Reports"
        }

        temp_config_path = os.path.join(tempfile.gettempdir(), f"post_migration_{conversation_key}.json")
        with open(temp_config_path, 'w') as f:
            json.dump(post_config, f, indent=2)

        # Execute validation
        result = execute_post_migration_check(
            config_file_path=temp_config_path,
            say_callback=say_callback
        )

        # Upload report if available
        if result.get('success') and result.get('report_path') and channel_id:
            self._upload_report(result['report_path'], channel_id, say_callback)

        # Clean up temp file
        try:
            os.remove(temp_config_path)
        except:
            pass

        # Clear stored migration config
        del self.last_migration_config[conversation_key]

        # Update conversation history
        self._update_conversation_history(
            conversation_key, "yes", result,
            operation="Post-Migration Validation"
        )

        return result.get('message', str(result))

    def _upload_report(self, report_path, channel_id, say_callback):
        """
        Upload Excel report to Slack.

        Args:
            report_path: Path to the report file
            channel_id: Slack channel ID
            say_callback: Slack callback for error messages
        """
        try:
            # Convert to absolute path if relative
            if not os.path.isabs(report_path):
                report_path = os.path.abspath(report_path)

            # Extract filename from path for proper download name
            report_filename = os.path.basename(report_path)

            logger.info(f"Uploading report from: {report_path}")

            self.app.client.files_upload_v2(
                channel=channel_id,
                file=report_path,
                filename=report_filename,
                title=report_filename,
                initial_comment="📊 Here's your validation report!"
            )
            logger.info("Successfully uploaded report")
        except Exception as e:
            logger.error(f"Failed to upload report: {str(e)}", exc_info=True)
            if say_callback:
                say_callback(f"⚠️  Report generated at `{report_path}` but upload to Slack failed. You can retrieve it from that path.")

    def _update_conversation_history(self, conversation_key, user_input, result, operation=None):
        """
        Update conversation history with user input and the tool result.

        The result is stored as an explicit "executed operation" record (with its
        success/failure outcome) rather than a bare message, so that on later turns
        the model can accurately answer questions like "why did the deployment fail?"
        instead of denying an operation was ever run.

        Args:
            conversation_key: Conversation context key
            user_input: User's input message
            result: Tool execution result (dict or str)
            operation: Optional human-readable operation name (e.g. "CI/CD Migration")
        """
        self.conversation_history[conversation_key].append(HumanMessage(content=user_input))

        if isinstance(result, dict):
            message = result.get('message', str(result))
            succeeded = result.get('success', result.get('migration_completed'))
            outcome = ""
            if succeeded is True:
                outcome = " (OUTCOME: SUCCEEDED)"
            elif succeeded is False:
                outcome = " (OUTCOME: FAILED)"
        else:
            message = result
            outcome = ""

        label = f"[Executed operation: {operation}]{outcome}\n" if operation else (f"[Tool result]{outcome}\n" if outcome else "")
        self.conversation_history[conversation_key].append(AIMessage(content=f"{label}{message}"))

    def _format_result(self, result):
        """
        Format tool execution result for display.

        Args:
            result: Tool execution result

        Returns:
            Formatted string message
        """
        if isinstance(result, dict):
            return result.get('message', str(result))
        return result

    def start(self):
        """Start the Slack bot in Socket Mode."""
        try:
            logger.info("🚀 Starting Refactored CI/CD & IDMC Automation Agent...")
            logger.info("📋 Features:")
            logger.info("   • Pre-Migration Check (modular tool)")
            logger.info("   • CI/CD Migration (modular tool)")
            logger.info("   • Post-Migration Validation (modular tool)")
            logger.info("   • IDMC Operations (modular tool)")
            logger.info("   • Conversational AI powered by Claude Opus 4.8")
            logger.info("   • Real-time progress updates")
            logger.info("")
            logger.info("⚡ Bot is now listening for messages and mentions...")

            handler = SocketModeHandler(self.app, self.slack_app_token)
            handler.start()

        except Exception as e:
            logger.error(f"❌ Failed to start agent: {str(e)}", exc_info=True)
            raise

    def __repr__(self) -> str:
        return "Agent(Refactored CI/CD & IDMC Automation Assistant)"


if __name__ == "__main__":
    try:
        agent = Agent()
        agent.start()
    except KeyboardInterrupt:
        logger.info("\n👋 Agent stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}", exc_info=True)
