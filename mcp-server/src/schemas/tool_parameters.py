"""
Pydantic models for MCP tool parameters.

These models replace Dict[str, Any] parameters to ensure compatibility with
Google Gemini's function calling API, which doesn't support additionalProperties.

Following best practices from:
- Google Gemini function calling docs
- Pydantic AI type safety guidelines
- MCP protocol standardization
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class WorkflowCustomization(BaseModel):
    """
    Customizations for workflow templates.

    Allows modifying template workflows by adding or removing states/actions
    without using dynamic dict structures that Gemini can't handle.
    """
    additional_states: Optional[List[str]] = Field(
        default=None,
        description="Additional states to add to the template workflow"
    )
    additional_actions: Optional[List[str]] = Field(
        default=None,
        description="Additional actions/transitions to add to the workflow"
    )
    skip_states: Optional[List[str]] = Field(
        default=None,
        description="States from template to skip/exclude"
    )
    description_override: Optional[str] = Field(
        default=None,
        description="Override the template's default description"
    )

    class Config:
        """Pydantic config for Gemini compatibility."""
        extra = "forbid"  # Prevent additionalProperties in JSON schema


class PermissionUpdate(BaseModel):
    """
    Permission update specification for workflow access control.

    Defines who can perform actions in the workflow using explicit structure
    instead of dict[str, str] which Gemini doesn't support.
    """
    slug: str = Field(
        description="Permission identifier (e.g., 'manager_approval_perm')"
    )
    description: str = Field(
        description="Human-readable permission description"
    )

    class Config:
        """Pydantic config for Gemini compatibility."""
        extra = "forbid"  # Prevent additionalProperties in JSON schema


class FormField(BaseModel):
    """
    Form field specification for workflow data collection.

    Defines input fields for workflow actions that require user data.
    Uses explicit typing instead of dynamic dicts for Gemini compatibility.
    """
    key: str = Field(
        description="Field identifier/name"
    )
    type: Literal["string", "date", "number", "boolean", "select"] = Field(
        description="Field data type"
    )
    required: bool = Field(
        default=False,
        description="Whether field is mandatory"
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="Available options for select fields"
    )
    label: Optional[str] = Field(
        default=None,
        description="Human-readable field label"
    )

    class Config:
        """Pydantic config for Gemini compatibility."""
        extra = "forbid"  # Prevent additionalProperties in JSON schema


class WorkflowAction(BaseModel):
    """
    Workflow action/transition specification.

    Defines state transitions in the workflow using explicit Pydantic model
    instead of Dict[str, Any] for Gemini function calling compatibility.
    """
    slug: str = Field(
        description="Action identifier (e.g., 'submit_for_review')"
    )
    from_state: str = Field(
        alias="from",
        description="Source state slug"
    )
    to_state: str = Field(
        alias="to",
        description="Destination state slug"
    )
    permission: str = Field(
        description="Required permission slug for this action"
    )
    requires_form: bool = Field(
        default=False,
        alias="requiresForm",
        description="Whether this action requires a form to be filled"
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable action name"
    )

    class Config:
        """Pydantic config for Gemini compatibility and camelCase support."""
        populate_by_name = True
        allow_population_by_field_name = True
        extra = "forbid"  # Prevent additionalProperties in JSON schema
