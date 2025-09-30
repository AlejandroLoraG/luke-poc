import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.mcp import MCPServerStreamableHTTP

from ..core.config import settings
from ..core.system_prompts import SystemPrompts, PromptMode


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


class WorkflowConversationAgent:
    def __init__(self, test_mode: bool = False, use_modular_prompts: bool = True):
        self.test_mode = test_mode
        self.use_modular_prompts = use_modular_prompts
        self.current_mode: Optional[PromptMode] = None

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
- For NEW workflows: Use 'create_workflow_from_description' or 'create_workflow_from_template' tools
- For EXISTING workflows: Use 'get_workflow', 'update_workflow_actions', 'add_workflow_state' tools
- For TEMPLATES: Use 'get_workflow_templates' to show available templates
- NEVER use 'create_workflow' - always use the new business-friendly creation tools
- Always present results in business terms, never expose technical details
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
    ) -> tuple[str, List[str]]:
        """
        Have a conversation about the workflow using MCP tools.
        Returns: (response_text, list_of_tools_used)
        """
        # Extract metadata from user_context
        conversation_id = user_context.get("conversation_id", "") if user_context else ""
        turn_count = user_context.get("turn_count", 0) if user_context else 0
        conversation_workflows = user_context.get("conversation_workflows", []) if user_context else []

        # Create properly typed context
        context = WorkflowContext(
            conversation_id=conversation_id,
            turn_count=turn_count,
            workflow_spec=workflow_spec,
            conversation_workflows=conversation_workflows
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

        # Run the agent with MCP tools
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

                    # Extract tools used (MCP tools are tracked automatically)
                    tools_used = getattr(result, 'tools_used', [])

            return response_text, tools_used

        except Exception as e:
            return f"I encountered an error: {str(e)}", []

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

        # Create properly typed context
        context = WorkflowContext(
            conversation_id=conversation_id,
            turn_count=turn_count,
            workflow_spec=workflow_spec,
            conversation_workflows=conversation_workflows
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
                        tools_used = getattr(result, 'tools_used', [])

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
                    tools_used = getattr(result, 'tools_used', [])
                    yield new_content, tools_used, sequence_id
                previous_content = current_content
            else:
                # First chunk or non-incremental content
                sequence_counter += 1
                sequence_id = f"seq_{sequence_counter}_{int(time.time() * 1000)}"
                tools_used = getattr(result, 'tools_used', [])
                yield current_content, tools_used, sequence_id
                previous_content = current_content