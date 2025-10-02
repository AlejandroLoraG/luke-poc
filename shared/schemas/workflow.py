from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class StateType(str, Enum):
    INITIAL = "initial"
    INTERMEDIATE = "intermediate"
    FINAL = "final"


class FieldType(str, Enum):
    STRING = "string"
    DATE = "date"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"


class Language(str, Enum):
    """Supported languages for AI agent responses."""
    ENGLISH = "en"
    SPANISH = "es"


class WorkflowField(BaseModel):
    key: str
    type: FieldType
    required: bool = False
    options: Optional[List[str]] = None


class WorkflowForm(BaseModel):
    name: str
    fields: List[WorkflowField]


class WorkflowState(BaseModel):
    slug: str
    name: str
    type: StateType


class WorkflowAction(BaseModel):
    slug: str
    from_: str = Field(alias="from")
    to: str
    requires_form: bool = Field(alias="requiresForm", default=False)
    permission: str
    form: Optional[WorkflowForm] = None

    class Config:
        populate_by_name = True


class WorkflowPermission(BaseModel):
    slug: str
    description: Optional[str] = None


class WorkflowEvent(BaseModel):
    event: str
    to: Optional[str] = None


class WorkflowEffect(BaseModel):
    type: str
    params: Dict[str, Any]


class WorkflowAutomation(BaseModel):
    slug: str
    on: WorkflowEvent
    effect: WorkflowEffect


class WorkflowSpec(BaseModel):
    spec_id: str = Field(alias="specId")
    spec_version: int = Field(alias="specVersion", default=1)
    tenant_id: str = Field(alias="tenantId", default="luke_123")
    name: str
    slug: str
    states: List[WorkflowState] = Field(default_factory=list)
    actions: List[WorkflowAction] = Field(default_factory=list)
    permissions: List[WorkflowPermission] = Field(default_factory=list)
    automations: List[WorkflowAutomation] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class WorkflowStateTransitionRequest(BaseModel):
    spec_id: str
    current_state: str
    action_slug: str
    user_id: str
    tenant_id: str
    form_data: Optional[Dict[str, Any]] = None


class WorkflowStateTransitionResponse(BaseModel):
    success: bool
    new_state: Optional[str] = None
    message: str
    validation_errors: Optional[List[str]] = None


class ChatRequest(BaseModel):
    message: str
    workflow_spec: Optional[WorkflowSpec] = None
    workflow_id: Optional[str] = None
    conversation_id: Optional[str] = None
    language: Language = Language.ENGLISH


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    prompt_count: int
    mcp_tools_used: List[str] = []
    mcp_tools_requested: List[str] = []  # Tools the AI wants to call (for UI display)
    workflow_created_id: Optional[str] = None  # Workflow ID if one was created
    workflow_source: Optional[str] = None
    language: str


class StreamingChatChunk(BaseModel):
    type: str  # "start", "chunk", "complete", "error"
    content: Optional[str] = None  # For "chunk" type
    conversation_id: Optional[str] = None
    prompt_count: Optional[int] = None
    mcp_tools_used: Optional[List[str]] = None
    workflow_source: Optional[str] = None
    error: Optional[str] = None  # For "error" type


class WorkflowPartialUpdateRequest(BaseModel):
    """
    Model for partial workflow updates. All fields are optional to support
    selective updates of workflow components.
    """
    name: Optional[str] = None
    slug: Optional[str] = None
    states: Optional[List[WorkflowState]] = None
    actions: Optional[List[WorkflowAction]] = None
    permissions: Optional[List[WorkflowPermission]] = None
    automations: Optional[List[WorkflowAutomation]] = None
    spec_version: Optional[int] = Field(alias="specVersion", default=None)

    class Config:
        populate_by_name = True


class WorkflowUpdateValidation(BaseModel):
    """
    Validation result for workflow updates with detailed feedback.
    """
    is_valid: bool = Field(alias="isValid")
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    affected_components: List[str] = Field(alias="affectedComponents", default_factory=list)
    auto_fixes_applied: List[str] = Field(alias="autoFixesApplied", default_factory=list)

    class Config:
        populate_by_name = True


class WorkflowStructureUpdate(BaseModel):
    """
    Model for workflow structure updates (name, description, metadata).
    """
    name: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None

    class Config:
        populate_by_name = True


class WorkflowFlowUpdate(BaseModel):
    """
    Model for workflow flow updates (states and actions).
    """
    states: Optional[List[WorkflowState]] = None
    actions: Optional[List[WorkflowAction]] = None
    maintain_existing_transitions: bool = Field(alias="maintainExistingTransitions", default=True)

    class Config:
        populate_by_name = True