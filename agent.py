"""
CI/CD Deployment and IDMC Automation Assistant with Slack Integration

Clean separation of concerns:
1. Agent class - Handles Slack communication and message routing
2. Tool modules - Self-contained, reusable functions for each operation
3. Business logic - Encapsulated within tool modules

This design allows:
- Easy testing of individual tools
- Reusable tool functions outside of Slack context
- Clear separation between orchestration and execution
- Simplified agent code focused on routing
"""

import os
import logging
import httpx
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


@tool
def save_config_file(filename: str, config_data: dict) -> str:
    r"""
    Save CI/CD configuration to a JSON file in the default configs directory.

    Args:
        filename: Name of the config file (e.g., 'test_plp.json')
        config_data: Dictionary containing the configuration data

    Returns:
        Full path to the saved configuration file
    """
    import json
    import os

    # Use relative path from project root
    default_path = os.path.join(os.path.dirname(__file__), "Configs")

    if not filename.endswith('.json'):
        filename += '.json'

    file_path = os.path.join(default_path, filename)

    try:
        os.makedirs(default_path, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)

        return f"""✅ Configuration saved successfully to: `{file_path}`

Would you like to proceed with this configuration?
Reply with *"yes"* to start the operation."""

    except Exception as e:
        return f"❌ Failed to save configuration: {str(e)}"


SYSTEM_PROMPT = """You are a CI/CD Deployment and IDMC Automation Assistant.

INTENT ROUTING

1. Pre-Migration Check
   - Validate source assets before migration
   - Check assets with pre-migration tags
   - Generate Excel report of assets to be migrated
   - Identify potential issues before migration

2. CI/CD Migration & Deployment
   - Migrate assets between Source and Target organizations
   - Support:
     a. Upload shared configuration file
     b. Use configuration file already available on server
     c. Collect deployment details through chat

3. Post-Migration Check
   - Validate migrated assets
   - Generate Excel reports
   - Can be run independently or after migration

4. IDMC Functionalities
   a. Asset Management (get objects, query by type/path)
   b. Tag Management (add/remove tags)
   c. Project Management (create/update/delete)
   d. Folder Management (create/update/delete)
   e. Schedule Management (create/update/delete/query)
   f. Agent Management (get agents, status, runtime environments)
   g. User Management (get/create/delete users)
   h. Permission Management (object permissions)

IMPORTANT - TAGGING RESTRICTIONS

PROJECT and FOLDER asset types DO NOT support tagging in IDMC.
Before calling tag_assets or untag_assets:
- Filter out any assets where type='PROJECT' or type='FOLDER'
- Inform the user that these types were excluded
- Only pass taggable asset types (DTEMPLATE, MTT, CONNECTION, etc.)

COUNT QUERY DETECTION

When the user asks ONLY for the count or number of items, set is_count_query=True:
- "how many mappings"
- "give me count of projects"
- "total number of users"
- "count of schedules"

When the user wants full details, list, or report, set is_count_query=False:
- "list all mappings"
- "show me all projects"
- "get details of users"
- "give me report of schedules"

WELCOME MENU

Display the welcome menu only when:
- User sends a greeting
- User asks what the assistant can do
- User input cannot be mapped to a supported capability

When displaying the welcome menu, always present options as a numbered list (1, 2, 3).

WORKFLOW RULES

- Maintain conversation context - CRITICAL: Track tags, folder paths, project names, asset IDs used in the conversation
- Do not request information already provided
- Ask one question at a time
- Confirm inputs before execution
- Provide real-time execution status updates
- After identifying the intent, proceed directly to the relevant workflow
- If the user's intent matches a supported capability, start the corresponding workflow immediately

CONTEXT TRACKING

Pay close attention to:
- Tag names used in tagging operations (remember them for subsequent list/query operations)
- Folder paths mentioned (use them to filter results)
- Project names referenced
- Asset types being worked with

When user says "list assets with tag X" after tagging with X:
- Use the exact tag name from previous operations
- Apply query filter: q=tags contains 'TagName'
- Don't return all assets, only filtered ones

SLACK FORMATTING RULES (IMPORTANT)

- Use *text* for bold (single asterisk, not double)
- Use _text_ for italic
- Use `text` for inline code
- Use :emoji_name: for emojis (e.g., :white_check_mark:, :rocket:, :gear:)
- Use numbered lists: 1., 2., 3.
- Use bullet points: •
- Never use **text** (double asterisks) - it won't render as bold in Slack
- Keep formatting clean and professional
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
            model="claude-sonnet-4-20250514",
            api_key=self.anthropic_auth_token,
            base_url=self.anthropic_base_url + "/v1",
            http_client=httpx.Client(verify=False)
        ).bind_tools([
            save_config_file,
            pre_migration_check_tool,
            cicd_migration_tool,
            post_migration_check_tool,
            idmc_operations_tool
        ])

        self.conversation_history = {}
        self.last_migration_config = {}  # For Post-Migration confirmation
        self.last_pre_migration_config = {}  # For CICD Migration confirmation

        self._register_handlers()

        logger.info("✅ Refactored Agent initialized successfully")

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
        Handle file attachments in messages.

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
                file_id = file_obj.get("id")
                download_url = file_obj.get("url_private_download")

                logger.info(f"📎 Processing file: {filename} from user {user_id}")

                # Only process JSON config files
                if not filename.endswith('.json'):
                    say(f"⚠️  Only JSON configuration files are supported. Received: `{filename}`\n\nPlease upload a `.json` file.")
                    continue

                # Download the file
                import requests
                import os
                import json

                headers = {"Authorization": f"Bearer {self.slack_bot_token}"}
                response = requests.get(download_url, headers=headers)

                if response.status_code != 200:
                    say(f"❌ Failed to download file: `{filename}`")
                    logger.error(f"Download failed with status {response.status_code}")
                    continue

                # Save to Configs folder (relative path from agent.py location)
                configs_dir = os.path.join(os.path.dirname(__file__), "Configs")
                os.makedirs(configs_dir, exist_ok=True)

                file_path = os.path.join(configs_dir, filename)

                # Validate JSON before saving
                try:
                    json_content = json.loads(response.content)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_content, f, indent=2)

                    # Add to conversation history so LLM knows about it
                    if conversation_key not in self.conversation_history:
                        self.conversation_history[conversation_key] = []

                    self.conversation_history[conversation_key].append(
                        HumanMessage(content=f"[User uploaded config file: {filename}]")
                    )
                    self.conversation_history[conversation_key].append(
                        AIMessage(content=f"✅ Configuration file saved: `{filename}`\n\nWhat would you like to do?\n1️⃣ Run pre-migration check\n2️⃣ Run CI/CD migration\n3️⃣ Run post-migration validation\n4️⃣ Just keep it for later")
                    )

                    say(f"✅ Configuration file saved: `{filename}`\n\n*What would you like to do?*\n1️⃣ Run pre-migration check\n2️⃣ Run CI/CD migration\n3️⃣ Run post-migration validation\n4️⃣ Just keep it for later")

                    logger.info(f"✅ Saved config file: {file_path}")

                except json.JSONDecodeError as e:
                    say(f"❌ Invalid JSON file: {str(e)}\n\nPlease check your JSON syntax and upload again.")
                    logger.error(f"JSON parsing error: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"❌ Error handling file in message: {str(e)}", exc_info=True)
            say(f"❌ Error processing file: {str(e)}")

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

            # Get Claude response using agent (pass channel_id for file uploads)
            response = self._get_claude_response(conversation_key, text, say, channel_id)

            # Keep last 20 messages for context
            if len(self.conversation_history[conversation_key]) > 20:
                self.conversation_history[conversation_key] = self.conversation_history[conversation_key][-20:]

            # Send response to Slack if not already sent by tool
            if response and not response.startswith("🚀") and not response.startswith("🔍") and not response.startswith("🔧"):
                say(response)

            logger.info(f"✅ Sent response to user {user_id}")

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}", exc_info=True)
            say(f"❌ Sorry, I encountered an error: {str(e)}")

    def _get_claude_response(self, conversation_key: str, user_input: str, say_callback=None, channel_id=None) -> str:
        """
        Get response from Claude AI and route to appropriate tool.

        Args:
            conversation_key: Unique key for conversation context
            user_input: User's message
            say_callback: Slack say function for real-time updates
            channel_id: Slack channel ID for file uploads

        Returns:
            Claude's response text
        """
        try:
            chat_history = self.conversation_history[conversation_key]

            # Add system message if first message
            messages = []
            if not chat_history:
                messages.append(SystemMessage(content=SYSTEM_PROMPT))

            messages.extend(chat_history)
            messages.append(HumanMessage(content=user_input))

            # Check if user is responding "yes" to pre-migration completion (proceed to CICD)
            if conversation_key in self.last_pre_migration_config and user_input.lower().strip() in ['yes', 'y', 'proceed', 'continue']:
                return self._handle_cicd_migration_confirmation(conversation_key, say_callback, channel_id)

            # Check if user is responding "yes" to post-migration prompt
            if conversation_key in self.last_migration_config and user_input.lower().strip() in ['yes', 'y', 'proceed', 'continue']:
                return self._handle_post_migration_confirmation(conversation_key, say_callback, channel_id)

            # Get response from LLM
            response = self.llm.invoke(messages)

            # Check if tool calls are present
            if hasattr(response, 'tool_calls') and response.tool_calls:
                return self._handle_tool_calls(response.tool_calls, conversation_key, user_input, say_callback, channel_id)

            # No tool call, just return the response
            response_text = response.content

            # Update conversation history
            self.conversation_history[conversation_key].append(HumanMessage(content=user_input))
            self.conversation_history[conversation_key].append(AIMessage(content=response_text))

            return response_text

        except Exception as e:
            logger.error(f"❌ Error getting Claude response: {str(e)}", exc_info=True)
            return f"❌ Sorry, I couldn't process your request: {str(e)}"

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
            Result message from tool execution
        """
        for tool_call in tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']

            # Route to CICD Migration Tool
            if tool_name == 'cicd_migration_tool':
                result = execute_cicd_migration(
                    config_file_path=tool_args['config_file_path'],
                    say_callback=say_callback
                )

                # Store migration config for post-migration validation
                if isinstance(result, dict) and result.get('migration_completed'):
                    self.last_migration_config[conversation_key] = result

                self._update_conversation_history(conversation_key, user_input, result)
                return self._format_result(result)

            # Route to Pre-Migration Check Tool
            elif tool_name == 'pre_migration_check_tool':
                result = execute_pre_migration_check(
                    config_file_path=tool_args['config_file_path'],
                    say_callback=say_callback
                )

                # Upload report if available
                if result.get('success') and result.get('report_path') and channel_id:
                    self._upload_report(result['report_path'], channel_id, say_callback)

                # Store pre-migration config for CICD migration prompt
                if isinstance(result, dict) and result.get('success'):
                    self.last_pre_migration_config[conversation_key] = {
                        'config_file_path': tool_args['config_file_path']
                    }

                self._update_conversation_history(conversation_key, user_input, result)
                return self._format_result(result)

            # Route to Post-Migration Check Tool
            elif tool_name == 'post_migration_check_tool':
                result = execute_post_migration_check(
                    config_file_path=tool_args['config_file_path'],
                    say_callback=say_callback
                )

                # Upload report if available
                if result.get('success') and result.get('report_path') and channel_id:
                    self._upload_report(result['report_path'], channel_id, say_callback)

                self._update_conversation_history(conversation_key, user_input, result)
                return self._format_result(result)

            # Route to IDMC Operations Tool
            elif tool_name == 'idmc_operations_tool':
                import json
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

                self._update_conversation_history(conversation_key, user_input, result)
                return self._format_result(result)

            # Route to Save Config Tool
            elif tool_name == 'save_config_file':
                tool_result = save_config_file.invoke(tool_args)
                self._update_conversation_history(conversation_key, user_input, tool_result)
                return tool_result

        return "No matching tool found"

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
        from tools.cicd_tool import execute_cicd_migration

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
        self._update_conversation_history(conversation_key, "yes", result)

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
        import json
        import tempfile
        import os

        migration_info = self.last_migration_config[conversation_key]

        # Show config preview
        config_preview = f"""📋 *Post-Migration Validation Configuration:*

🎯 *Target Environment:*
   • Username: `{migration_info['target_username']}`
   • Password: `{'*' * 8}`
   • Region: `{migration_info['target_region']}`

📦 *Validation Details:*
   • Project: `{migration_info['project_name']}`
   • Tags to Check: `{', '.join(migration_info['post_migration_tag'])}`

Proceeding with validation..."""

        if say_callback:
            say_callback(config_preview)

        # Create temp config file
        post_config = {
            "IICS_TGT_username": migration_info['target_username'],
            "IICS_TGT_password": migration_info['target_password'],
            "IICS_TGT_region": migration_info['target_region'],
            "PostMigration_Tag": migration_info['post_migration_tag'],
            "ProjectName": migration_info['project_name'],
            "logFileDir": "Logs",
            "file_dir": "Reports",
            "file_name": "post_migration_validation.xlsx"
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
        self._update_conversation_history(conversation_key, "yes", result)

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
            import os
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
            logger.error(f"Failed to upload report: {str(e)}")
            if say_callback:
                say_callback(f"⚠️  Report generated at `{report_path}` but upload failed: {str(e)}")

    def _update_conversation_history(self, conversation_key, user_input, result):
        """
        Update conversation history with user input and result.

        Args:
            conversation_key: Conversation context key
            user_input: User's input message
            result: Tool execution result
        """
        self.conversation_history[conversation_key].append(HumanMessage(content=user_input))

        if isinstance(result, dict):
            message = result.get('message', str(result))
        else:
            message = result

        self.conversation_history[conversation_key].append(AIMessage(content=message))

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
            logger.info("   • Conversational AI powered by Claude Sonnet 4")
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
