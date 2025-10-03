import json
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.mcp import MCPServerStreamableHTTP

from ..core.config import settings
from ..core.system_prompts import SystemPrompts, PromptMode
from ..core.debug_client import DebugWorkflowClient

logger = logging.getLogger(__name__)


@dataclass
class WorkflowContext:
    """
    Dependency context for Pydantic AI workflow agent.

    Following Pydantic AI best practices for type-safe dependency injection.
    See: https://ai.pydantic.dev/dependencies/

    This dataclass carries conversation metadata and workflow state for the agent.
    Note: Full conversation history is passed separately in the prompt, not here.
    """
    # Conversation metadata
    conversation_id: str = ""
    turn_count: int = 0

    # Current workflow being discussed (optional)
    workflow_spec: Optional[Dict[str, Any]] = None

    # Workflows created/modified in this conversation session
    # Format: [{"spec_id": "wf_xyz", "name": "Task Management", "action": "created"}]
    conversation_workflows: List[Dict[str, str]] = field(default_factory=list)

    # User identity (for future multi-tenancy)
    tenant_id: str = "luke_123"
    user_id: Optional[str] = None

    # Language preference for AI responses
    language: str = "en"  # ISO 639-1 code: "en" or "es"

    # Session and binding context (NEW)
    session_id: Optional[str] = None
    bound_workflow_id: Optional[str] = None  # Workflow this chat is locked to
    is_workflow_bound: bool = False  # True if chat is bound to a workflow

    def add_workflow_reference(self, spec_id: str, name: str, action: str = "discussed"):
        """
        Track a workflow mentioned in this conversation.

        Args:
            spec_id: Workflow specification ID
            name: Business-friendly workflow name
            action: What happened (created, modified, discussed)
        """
        self.conversation_workflows.append({
            "spec_id": spec_id,
            "name": name,
            "action": action
        })

    def get_recent_workflows(self, limit: int = 5) -> List[Dict[str, str]]:
        """
        Get most recent workflow references.

        Args:
            limit: Maximum number of workflows to return

        Returns:
            List of recent workflow references
        """
        return self.conversation_workflows[-limit:] if self.conversation_workflows else []

    def can_create_new_workflow(self) -> bool:
        """
        Check if this chat can create a new workflow.

        Returns:
            False if already bound to a workflow, True otherwise
        """
        return not self.is_workflow_bound


class WorkflowConversationAgent:
    def __init__(self, test_mode: bool = False, use_modular_prompts: bool = True):
        self.test_mode = test_mode
        self.use_modular_prompts = use_modular_prompts
        self.current_mode: Optional[PromptMode] = None

        # Initialize debug mode client if enabled
        self.debug_mode = settings.debug_mode
        self.debug_client: Optional[DebugWorkflowClient] = None
        if self.debug_mode and not test_mode:
            self.debug_client = DebugWorkflowClient(settings.svc_builder_url)
            logger.warning(f"⚠️  DEBUG MODE ENABLED - Using direct API calls to {settings.svc_builder_url}")
            logger.warning("⚠️  This bypasses MCP layer for diagnostic purposes")

        # Initialize the model
        if test_mode:
            model = TestModel()
        else:
            os.environ['GOOGLE_API_KEY'] = settings.google_api_key
            model = GoogleModel(settings.ai_model)

        # Initialize MCP Server connection
        if not test_mode:
            self.mcp_server = MCPServerStreamableHTTP(f"{settings.mcp_server_url}/mcp")
            toolsets = [self.mcp_server]
        else:
            # In test mode, use empty toolsets
            toolsets = []

        # Create the agent with MCP toolsets
        # Use general prompt as base when modular prompts enabled
        base_instructions = (
            SystemPrompts.get_prompt(PromptMode.GENERAL)
            if use_modular_prompts
            else self._get_legacy_system_instructions()
        )

        self.agent = Agent(
            model=model,
            deps_type=WorkflowContext,
            instructions=base_instructions,
            toolsets=toolsets
        )

        # Register dynamic language instruction (Pydantic AI best practice)
        @self.agent.system_prompt
        def add_language_instruction(ctx: RunContext[WorkflowContext]) -> str:
            """
            Dynamic instruction that adds language-specific guidance.

            Following Pydantic AI best practices:
            - Uses @agent.system_prompt decorator for dynamic instructions
            - Accesses dependencies via RunContext type-safe injection
            - Re-evaluated on each run for fresh context

            Args:
                ctx: RunContext with WorkflowContext dependency

            Returns:
                Language instruction string (empty for English)
            """
            from ..core.language_instructions import get_language_instruction
            return get_language_instruction(ctx.deps.language)

        # Register dynamic workflow binding constraint (Pydantic AI best practice)
        @self.agent.system_prompt
        def add_workflow_binding_constraint(ctx: RunContext[WorkflowContext]) -> str:
            """
            Dynamic instruction that enforces workflow binding rules.

            If a chat is bound to a workflow, the agent can ONLY interact with that
            workflow (view, update, manage). It cannot create new workflows or switch
            to different workflows.

            Following Pydantic AI best practices:
            - Uses @agent.system_prompt decorator for dynamic constraints
            - Accesses binding state via RunContext dependency injection
            - Provides context-aware instructions based on binding status

            Args:
                ctx: RunContext with WorkflowContext dependency

            Returns:
                Binding constraint instruction (empty if not bound)
            """
            if not ctx.deps.is_workflow_bound:
                return ""  # No constraints if not bound

            workflow_id = ctx.deps.bound_workflow_id
            workflow_name = ctx.deps.workflow_spec.get("name", "Unknown") if ctx.deps.workflow_spec else "your workflow"

            # Language-aware constraint messages
            if ctx.deps.language == "es":
                return f"""
🔒 RESTRICCIÓN IMPORTANTE DE FLUJO DE TRABAJO:

Este chat está vinculado EXCLUSIVAMENTE al flujo de trabajo: "{workflow_name}" (ID: {workflow_id})

PUEDES:
✅ Ver los detalles de este flujo de trabajo
✅ Actualizar este flujo de trabajo (estados, acciones, permisos)
✅ Responder preguntas sobre este flujo de trabajo
✅ Ayudar a gestionar este flujo de trabajo

NO PUEDES:
❌ Crear nuevos flujos de trabajo (este chat ya tiene uno)
❌ Cambiar a un flujo de trabajo diferente
❌ Listar o buscar otros flujos de trabajo

Si el usuario intenta crear un nuevo flujo de trabajo, explica amablemente:
"Este chat está dedicado a tu flujo de trabajo '{workflow_name}'. Para crear un nuevo flujo de trabajo, por favor inicia un nuevo chat en tu sesión."
"""
            else:  # English
                return f"""
🔒 IMPORTANT WORKFLOW BINDING CONSTRAINT:

This chat is EXCLUSIVELY bound to workflow: "{workflow_name}" (ID: {workflow_id})

YOU CAN:
✅ View details of this workflow
✅ Update this workflow (states, actions, permissions)
✅ Answer questions about this workflow
✅ Help manage this workflow

YOU CANNOT:
❌ Create new workflows (this chat already has one)
❌ Switch to a different workflow
❌ List or search other workflows

If the user tries to create a new workflow, politely explain:
"This chat is dedicated to your '{workflow_name}' workflow. To create a new workflow, please start a new chat in your session."
"""

    def _enhance_message_with_mode(
        self,
        message: str,
        mode: PromptMode,
        workflow_spec: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enhance message with mode-specific guidance.

        Args:
            message: Original user message
            mode: Inferred conversation mode
            workflow_spec: Optional workflow context

        Returns:
            Enhanced message with mode guidance prepended
        """
        if not self.use_modular_prompts:
            return message

        # Get mode-specific prompt
        mode_prompt = SystemPrompts.get_prompt(mode)

        # Build enhanced message with mode context
        enhanced = f"""[Mode: {mode.value.upper()}]

{mode_prompt}

---

User message: {message}"""

        return enhanced

    def get_current_mode(self) -> Optional[PromptMode]:
        """Get the currently active prompt mode."""
        return self.current_mode

    def get_mode_info(self) -> Dict[str, Any]:
        """
        Get information about current mode and token usage.

        Returns:
            Dictionary with mode info and stats
        """
        if not self.current_mode:
            return {
                "mode": "none",
                "token_estimate": 0,
                "token_reduction": 0.0
            }

        return {
            "mode": self.current_mode.value,
            "token_estimate": SystemPrompts.get_mode_stats().get(self.current_mode.value, 0),
            "token_reduction_percent": SystemPrompts.get_token_reduction(self.current_mode),
            "baseline_tokens": 2000
        }

    def _extract_tools_from_messages(self, result) -> List[str]:
        """
        Extract tool names from Pydantic AI message history.

        Pydantic AI tracks tool calls in the message history as ToolCallPart objects.
        This method extracts the tool names from those parts.

        Args:
            result: Pydantic AI RunResult object

        Returns:
            List of unique tool names that were called
        """
        tools = []
        try:
            # Get new messages from this run
            if not hasattr(result, 'new_messages'):
                logger.warning(f"Result object has no 'new_messages' method. Type: {type(result)}")
                return []

            messages = result.new_messages()

            for message in messages:
                # Check if message has parts (ModelResponse messages do)
                if hasattr(message, 'parts'):
                    for part in message.parts:
                        # ToolCallPart has a tool_name attribute
                        if hasattr(part, 'tool_name'):
                            tool_name = part.tool_name
                            tools.append(tool_name)
                            logger.debug(f"Extracted tool call: {tool_name}")

        except Exception as e:
            logger.error(f"Error extracting tools from messages: {e}", exc_info=True)

        # Remove duplicates and return
        unique_tools = list(set(tools))
        if unique_tools:
            logger.info(f"🔧 Tools used in this interaction: {unique_tools}")

        return unique_tools

    def _extract_workflow_id_from_result(self, result) -> Optional[str]:
        """
        Extract created workflow ID from tool result.

        Args:
            result: Pydantic AI RunResult object

        Returns:
            Workflow spec_id if a create tool was called, None otherwise
        """
        try:
            if not hasattr(result, 'new_messages'):
                return None

            messages = result.new_messages()

            for message in messages:
                # Look for ToolReturnPart which contains tool results
                if hasattr(message, 'parts'):
                    for part in message.parts:
                        # ToolReturnPart has tool_name and content
                        if hasattr(part, 'tool_name') and hasattr(part, 'content'):
                            # Check if it's a creation tool
                            if 'create_workflow' in part.tool_name:
                                # Parse the JSON result
                                try:
                                    import json
                                    result_data = json.loads(part.content) if isinstance(part.content, str) else part.content
                                    # Look for workflow_id, spec_id, or specId in the result
                                    workflow_id = (result_data.get('workflow_id') or
                                                 result_data.get('spec_id') or
                                                 result_data.get('specId'))
                                    if workflow_id:
                                        logger.info(f"📋 Extracted workflow ID: {workflow_id}")
                                        return workflow_id
                                except Exception as e:
                                    logger.debug(f"Could not parse workflow ID: {e}")
                                    continue

        except Exception as e:
            logger.error(f"Error extracting workflow ID: {e}", exc_info=True)

        return None

    def _get_legacy_system_instructions(self) -> str:
        return """You are a business process consultant and workflow design expert. Your role is to help organizations create and optimize their business processes through natural conversation.

FUNDAMENTAL IDENTITY:
You are NOT a technical system. You are a seasoned business analyst who specializes in workflow design, process optimization, and organizational efficiency. You speak the language of business, not technology.

CORE EXPERTISE:
- Business process design and optimization
- Workflow creation for various organizational needs
- Process analysis and improvement recommendations
- Stakeholder requirement gathering through conversation

CONVERSATION PRINCIPLES:

1. BUSINESS LANGUAGE ONLY:
   - Use terms: "process", "workflow", "steps", "stages", "transitions", "approvals", "tasks", "business flow"
   - NEVER mention: JSON, schemas, validation, IDs, slugs, specId, technical errors, data structures
   - Think like: "How does this help the business?" not "What fields are required?"

2. NATURAL REQUIREMENT GATHERING:
   - Listen to business needs: "We need to track document approvals"
   - Ask business questions: "Who needs to approve?" "What happens after approval?"
   - NEVER ask: "What should the specId be?" "What permission slugs do you want?"

3. WORKFLOW DESIGN METHODOLOGY:
   When creating workflows, follow this pattern:
   a) Understand the business need
   b) Propose a logical process flow
   c) Discuss roles and responsibilities
   d) Clarify decision points and transitions
   e) Build the workflow using available tools
   f) Present the completed process in business terms

WORKFLOW CREATION EXAMPLES:

❌ WRONG APPROACH:
"I need technical specifications. What should the specId be? What permission slugs should I use for each action?"

✅ CORRECT APPROACH:
"I'll design an approval process for you. Here's what I'm thinking:
1. **Submitted** - When someone requests approval
2. **Under Review** - When a manager evaluates the request
3. **Approved/Rejected** - The final decision is made

This gives you clear visibility into where each request stands. Would you like to customize any of these stages?"

TECHNICAL FIELD AUTO-GENERATION:
Behind the scenes, automatically generate all technical requirements:
- Workflow IDs from business purpose: "approval process" → "wf_approval"
- States from business stages: "Under Review" → "under_review"
- Actions from transitions: "Submit for approval" → "submit_for_approval"
- Permissions from roles: "Manager approval" → "manager_approval_perm"
- Always use tenantId: "luke_123" and specVersion: 1

ERROR HANDLING STRATEGY:
If technical issues arise:
- NEVER expose error messages or validation failures
- Instead say: "Let me refine that process design..."
- Try a simpler workflow structure
- Ask clarifying business questions
- Focus on what the user wants to achieve

WORKFLOW TEMPLATES KNOWLEDGE:
You can quickly design these common workflow types:
- **Approval Process**: Submit → Review → Approve/Reject
- **Incident Management**: Report → Investigate → Resolve
- **Task Management**: Create → In Progress → Complete
- **Document Review**: Draft → Review → Publish
- **Request Handling**: Submit → Process → Fulfill

MCP TOOL USAGE:

🔍 FINDING WORKFLOWS - MULTI-PASS SEARCH STRATEGY:
CRITICAL: NEVER give up after first search failure! Always try multiple strategies:

**Primary Search Strategy:**
1. Use 'find_workflow_by_any_means' tool FIRST - it's intelligent and tries multiple approaches
2. If no exact match, use partial matches from the results
3. If still no match, try 'get_conversation_workflows' for recent context

**Fallback Search Strategy (if primary fails):**
1. Try 'list_workflows' and manually search through results
2. Look for template-based matches (task → task management workflows)
3. Search for similar names or partial matches
4. Check recent workflows that might match user intent

**NEVER say "workflow not found" without trying at least 3 different search approaches!**

📝 WORKFLOW OPERATIONS:
- For NEW workflows: Use 'create_workflow_from_description' or 'create_workflow_from_template'
- For UPDATING workflows: Use the enhanced user-intent tools:
  * 'update_workflow_structure' - Rename workflows, update descriptions
  * 'modify_workflow_flow' - Change states, update process flow
  * 'update_workflow_permissions' - Modify access controls
  * 'configure_workflow_forms' - Set up data collection forms
- For FINDING workflows: Use 'find_workflow_by_any_means' (intelligent multi-strategy search)
- For CONTEXT: Use 'get_conversation_workflows' to see recently created/modified workflows
- For TEMPLATES: Use 'get_workflow_templates' to show available templates

🎯 INTELLIGENT WORKFLOW DISCOVERY:
**When users refer to workflows by name or want to modify them:**

✅ CORRECT APPROACH:
```
User: "I want to modify my task management workflow"
AI Process:
1. Call 'find_workflow_by_any_means' with "task management"
2. If found → proceed with modification
3. If not found → try 'get_conversation_workflows' for recent workflows
4. If still not found → try 'list_workflows' and search for "task" related workflows
5. Present options: "I found these task-related workflows: [list]. Which one would you like to modify?"
```

❌ WRONG APPROACH:
```
User: "I want to modify my task management workflow"
AI: "I couldn't find that workflow. Please provide the workflow ID."
```

🔧 ERROR RECOVERY PATTERNS:
If initial search fails:
1. **Try variations**: "task management" → try "task", "management", "My Task Management"
2. **Use context**: Check recent workflows from conversation
3. **Template matching**: If they mention "task", show all task-related workflows
4. **Offer alternatives**: "I found these similar workflows: [list]. Did you mean one of these?"
5. **Last resort**: Offer to create new workflow if none exist

🎯 WORKFLOW CREATION CONTEXT:
When creating workflows, immediately provide discoverable information:
- "I've created your '[name]' workflow. You can modify it by referring to '[name]' or '[template type]' workflow."
- Remember workflow names within the conversation context
- Proactively mention workflow aliases and search terms

❌ NEVER ask users for workflow IDs or technical specifications
✅ ALWAYS search intelligently using multiple strategies
✅ ALWAYS provide alternatives when exact matches aren't found
✅ ALWAYS maintain conversation context about created workflows
- Present results in business terms, never expose technical details
- If tool calls fail, handle gracefully without mentioning technical errors

CONVERSATION FLOW EXAMPLE:
User: "I need a workflow for customer complaints"
You: "Excellent! Customer complaint handling is crucial for service quality. I'll design a process that ensures every complaint gets proper attention:

1. **Received** - When the complaint first comes in
2. **Under Investigation** - While your team looks into the details
3. **Resolved** - When you've addressed the customer's concern

This process will help you track response times and ensure nothing falls through the cracks. Would you like to add any additional stages, such as an escalation step for complex complaints?"

Remember: You are helping businesses design better processes, not teaching them about technical systems. Focus on organizational impact, efficiency, and user experience."""


    async def chat(
        self,
        message: str,
        workflow_spec: Optional[Dict[str, Any]] = None,
        conversation_history: str = "",
        user_context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[str], Optional[str]]:
        """
        Have a conversation about the workflow using MCP tools.
        Returns: (response_text, list_of_tools_used, workflow_id_if_created)
        """
        # Extract metadata from user_context
        conversation_id = user_context.get("conversation_id", "") if user_context else ""
        turn_count = user_context.get("turn_count", 0) if user_context else 0
        conversation_workflows = user_context.get("conversation_workflows", []) if user_context else []
        language = user_context.get("language", "en") if user_context else "en"

        # Extract session and binding context (NEW)
        session_id = user_context.get("session_id") if user_context else None
        bound_workflow_id = user_context.get("bound_workflow_id") if user_context else None
        is_workflow_bound = user_context.get("is_workflow_bound", False) if user_context else False

        # Create properly typed context
        context = WorkflowContext(
            conversation_id=conversation_id,
            turn_count=turn_count,
            workflow_spec=workflow_spec,
            conversation_workflows=conversation_workflows,
            language=language,
            session_id=session_id,
            bound_workflow_id=bound_workflow_id,
            is_workflow_bound=is_workflow_bound
        )

        # Infer mode and enhance message if modular prompts enabled
        if self.use_modular_prompts:
            has_workflow = workflow_spec is not None
            self.current_mode = SystemPrompts.infer_mode(message, has_workflow)
            message = self._enhance_message_with_mode(message, self.current_mode, workflow_spec)

        # Build prompt with conversation history embedded
        full_prompt = message
        if conversation_history:
            full_prompt = f"Previous conversation:\n{conversation_history}\n\nCurrent question: {message}"

        # Add workflow context to the prompt if available
        if workflow_spec:
            workflow_summary = f"Current workflow: {workflow_spec.get('name', 'Unknown')} (ID: {workflow_spec.get('specId', 'unknown')})"
            full_prompt = f"{workflow_summary}\n\n{full_prompt}"

        # Run the agent with MCP tools with retry logic
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                if self.test_mode:
                    # In test mode, provide a simple response
                    response_text = "Test mode response: I understand your workflow question."
                    tools_used = []
                else:
                    # Use the MCP-enabled agent
                    async with self.agent:
                        result = await self.agent.run(full_prompt, deps=context)

                        # Get the response text from the result
                        if hasattr(result, 'data'):
                            response_text = result.data
                        elif hasattr(result, 'message'):
                            response_text = result.message
                        elif hasattr(result, 'output'):
                            response_text = result.output
                        else:
                            response_text = str(result)

                        # Handle any wrapper formats if needed
                        if hasattr(response_text, 'strip'):
                            response_text = response_text.strip()

                        # Extract tools used from message history
                        tools_used = self._extract_tools_from_messages(result)

                        # Extract workflow ID if created
                        workflow_id = self._extract_workflow_id_from_result(result)

                return response_text, tools_used, workflow_id

            except Exception as e:
                error_str = str(e)

                # Check if it's a retryable API error
                if attempt < max_retries and any(keyword in error_str.lower() for keyword in
                    ['500', 'internal', 'overloaded', 'retry', 'temporarily', 'unavailable']):

                    # Wait before retry (exponential backoff)
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    # Final attempt failed or non-retryable error
                    if '500' in error_str or 'INTERNAL' in error_str:
                        return ("I'm experiencing temporary connectivity issues with the AI service. "
                               "The workflow tools are still functional. Please try again in a moment, "
                               "or let me know what specific workflow operation you'd like to perform."), []
                    else:
                        return f"I encountered an error: {error_str}", []

        return "Service temporarily unavailable. Please try again.", []

    async def chat_stream(
        self,
        message: str,
        workflow_spec: Optional[Dict[str, Any]] = None,
        conversation_history: str = "",
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Stream a conversation about the workflow using MCP tools.

        This method provides streaming responses with proper deduplication and
        incremental content delivery for optimal user experience.

        Args:
            message: User message to process
            workflow_spec: Optional workflow specification for context
            conversation_history: Previous conversation for context
            user_context: Additional user context information

        Yields:
            Tuple of (chunk_text, tools_used, sequence_id) for each response chunk
        """
        import hashlib
        import time

        # Extract metadata from user_context
        conversation_id = user_context.get("conversation_id", "") if user_context else ""
        turn_count = user_context.get("turn_count", 0) if user_context else 0
        conversation_workflows = user_context.get("conversation_workflows", []) if user_context else []
        language = user_context.get("language", "en") if user_context else "en"

        # Extract session and binding context (NEW)
        session_id = user_context.get("session_id") if user_context else None
        bound_workflow_id = user_context.get("bound_workflow_id") if user_context else None
        is_workflow_bound = user_context.get("is_workflow_bound", False) if user_context else False

        # Create properly typed context
        context = WorkflowContext(
            conversation_id=conversation_id,
            turn_count=turn_count,
            workflow_spec=workflow_spec,
            conversation_workflows=conversation_workflows,
            language=language,
            session_id=session_id,
            bound_workflow_id=bound_workflow_id,
            is_workflow_bound=is_workflow_bound
        )

        # Infer mode and enhance message if modular prompts enabled
        if self.use_modular_prompts:
            has_workflow = workflow_spec is not None
            self.current_mode = SystemPrompts.infer_mode(message, has_workflow)
            message = self._enhance_message_with_mode(message, self.current_mode, workflow_spec)

        # Build the prompt with context
        full_prompt = self._build_contextual_prompt(message, conversation_history, workflow_spec)

        # Handle streaming based on mode
        try:
            if self.test_mode:
                async for chunk in self._generate_test_stream():
                    yield chunk
            else:
                async for chunk in self._generate_ai_stream(full_prompt, context):
                    yield chunk

        except Exception as e:
            # Yield error as a single chunk
            error_sequence_id = f"error_{int(time.time() * 1000)}"
            yield f"I encountered an error: {str(e)}", [], error_sequence_id

    def _build_contextual_prompt(
        self,
        message: str,
        conversation_history: str,
        workflow_spec: Optional[Dict[str, Any]]
    ) -> str:
        """Build a contextual prompt from message, history, and workflow spec."""
        full_prompt = message

        if conversation_history:
            full_prompt = f"Previous conversation:\n{conversation_history}\n\nCurrent question: {message}"

        if workflow_spec:
            workflow_summary = (
                f"Current workflow: {workflow_spec.get('name', 'Unknown')} "
                f"(ID: {workflow_spec.get('specId', 'unknown')})"
            )
            full_prompt = f"{workflow_summary}\n\n{full_prompt}"

        # Add conversation context reminder
        context_reminder = (
            "\nREMINDER: If user refers to workflows by name and they can't be found, "
            "use 'find_workflow_by_any_means' tool with multiple search strategies. "
            "Never give up after first search failure. Try partial matches, template matches, and recent workflows."
        )
        full_prompt = f"{full_prompt}{context_reminder}"

        return full_prompt

    async def _generate_test_stream(self):
        """Generate test streaming response for test mode."""
        test_chunks = [
            "Test ", "mode ", "streaming ", "response: ",
            "I understand ", "your workflow ", "question."
        ]
        for i, chunk in enumerate(test_chunks):
            yield chunk, [], f"test_{i}"

    async def _generate_ai_stream(self, prompt: str, context: WorkflowContext):
        """Generate AI streaming response using Pydantic AI."""
        import hashlib
        import time

        async with self.agent:
            async with self.agent.run_stream(prompt, deps=context) as result:
                content_hashes = set()
                sequence_counter = 0

                try:
                    # Primary streaming method: stream_text with delta=True
                    async for text_delta in result.stream_text(delta=True, debounce_by=None):
                        if not text_delta or not text_delta.strip():
                            continue

                        # Deduplication check
                        content_hash = hashlib.md5(text_delta.encode('utf-8')).hexdigest()
                        if content_hash in content_hashes:
                            continue

                        content_hashes.add(content_hash)
                        sequence_counter += 1

                        # Generate sequence ID and extract tools
                        sequence_id = f"seq_{sequence_counter}_{int(time.time() * 1000)}"
                        tools_used = self._extract_tools_from_messages(result)

                        yield text_delta, tools_used, sequence_id

                except (AttributeError, TypeError):
                    # Fallback: stream_output with incremental processing
                    async for chunk in self._fallback_stream_output(result, content_hashes, sequence_counter):
                        yield chunk

    async def _fallback_stream_output(self, result, content_hashes: set, sequence_counter: int):
        """Fallback streaming method using stream_output with incremental processing."""
        import hashlib
        import time

        previous_content = ""

        async for chunk in result.stream_output(debounce_by=None):
            current_content = str(chunk)

            # Deduplication check
            content_hash = hashlib.md5(current_content.encode('utf-8')).hexdigest()
            if content_hash in content_hashes:
                continue

            content_hashes.add(content_hash)

            # Extract incremental content
            if current_content.startswith(previous_content) and previous_content:
                new_content = current_content[len(previous_content):]
                if new_content:
                    sequence_counter += 1
                    sequence_id = f"seq_{sequence_counter}_{int(time.time() * 1000)}"
                    tools_used = self._extract_tools_from_messages(result)
                    yield new_content, tools_used, sequence_id
                previous_content = current_content
            else:
                # First chunk or non-incremental content
                sequence_counter += 1
                sequence_id = f"seq_{sequence_counter}_{int(time.time() * 1000)}"
                tools_used = self._extract_tools_from_messages(result)
                yield current_content, tools_used, sequence_id
                previous_content = current_content