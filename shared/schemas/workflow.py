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


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    prompt_count: int
    mcp_tools_used: List[str] = []
    workflow_source: Optional[str] = None


class StreamingChatChunk(BaseModel):
    type: str  # "start", "chunk", "complete", "error"
    content: Optional[str] = None  # For "chunk" type
    conversation_id: Optional[str] = None
    prompt_count: Optional[int] = None
    mcp_tools_used: Optional[List[str]] = None
    workflow_source: Optional[str] = None
    error: Optional[str] = None  # For "error" type