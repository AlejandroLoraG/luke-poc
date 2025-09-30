from fastapi import APIRouter, HTTPException, status
from typing import Dict, List, Any
from pydantic import BaseModel

from shared.schemas import WorkflowSpec
from shared.schemas.workflow import WorkflowPartialUpdateRequest, WorkflowUpdateValidation
from shared.schemas import ErrorCategory, ErrorCodes
from ..core.file_manager import file_manager
from ..core.error_handlers import ErrorHandler

router = APIRouter(prefix="/api/v1", tags=["workflows"])


class WorkflowCreateRequest(BaseModel):
    workflow_spec: WorkflowSpec


class WorkflowUpdateRequest(BaseModel):
    workflow_spec: WorkflowSpec


class WorkflowListResponse(BaseModel):
    workflows: List[Dict[str, Any]]
    total_count: int
    storage_stats: Dict[str, Any]


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(request: WorkflowCreateRequest) -> Dict[str, Any]:
    """
    Create a new workflow and save to file.
    """
    workflow_data = request.workflow_spec.model_dump(by_alias=True)
    spec_id = workflow_data.get("specId")

    if not spec_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow must have a specId"
        )

    # Check if workflow already exists
    if file_manager.workflow_exists(spec_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow with spec_id '{spec_id}' already exists"
        )

    # Save workflow to file
    success = file_manager.save_workflow(spec_id, workflow_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save workflow to file"
        )

    return {
        "message": "Workflow created successfully",
        "spec_id": spec_id,
        "name": workflow_data.get("name"),
        "version": workflow_data.get("specVersion", 1)
    }


@router.get("/workflows/{spec_id}")
async def get_workflow(spec_id: str) -> Dict[str, Any]:
    """
    Get a specific workflow by spec_id.
    """
    workflow_data = file_manager.load_workflow(spec_id)

    if workflow_data is None:
        error_response = ErrorHandler.workflow_not_found_error(spec_id, "get_workflow")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump()
        )

    return {
        "success": True,
        "operation": "get_workflow",
        "service": "svc-builder",
        "spec_id": spec_id,
        "workflow_spec": workflow_data
    }


@router.put("/workflows/{spec_id}")
async def update_workflow(spec_id: str, request: WorkflowUpdateRequest) -> Dict[str, Any]:
    """
    Update an existing workflow.
    """
    # Check if workflow exists
    if not file_manager.workflow_exists(spec_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with spec_id '{spec_id}' not found"
        )

    workflow_data = request.workflow_spec.model_dump(by_alias=True)

    # Ensure the spec_id matches
    if workflow_data.get("specId") != spec_id:
        workflow_data["specId"] = spec_id

    # Save updated workflow
    success = file_manager.save_workflow(spec_id, workflow_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow file"
        )

    return {
        "message": "Workflow updated successfully",
        "spec_id": spec_id,
        "name": workflow_data.get("name"),
        "version": workflow_data.get("specVersion", 1)
    }


@router.patch("/workflows/{spec_id}")
async def partial_update_workflow(spec_id: str, request: WorkflowPartialUpdateRequest) -> Dict[str, Any]:
    """
    Partially update an existing workflow with validation and auto-fixes.
    """
    # Check if workflow exists
    if not file_manager.workflow_exists(spec_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with spec_id '{spec_id}' not found"
        )

    # Convert request to dict, excluding None values
    partial_data = request.model_dump(by_alias=True, exclude_none=True)

    # Perform partial update with validation
    success, validation = file_manager.partial_update_workflow(spec_id, partial_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Partial update failed",
                "errors": validation.errors,
                "validation": validation.model_dump(by_alias=True)
            }
        )

    # Load updated workflow for response
    updated_workflow = file_manager.load_workflow(spec_id)

    return {
        "message": "Workflow partially updated successfully",
        "spec_id": spec_id,
        "name": updated_workflow.get("name"),
        "version": updated_workflow.get("specVersion", 1),
        "validation": validation.model_dump(by_alias=True),
        "affected_components": validation.affected_components,
        "auto_fixes_applied": validation.auto_fixes_applied
    }


@router.delete("/workflows/{spec_id}")
async def delete_workflow(spec_id: str) -> Dict[str, str]:
    """
    Delete a workflow file.
    """
    if not file_manager.workflow_exists(spec_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with spec_id '{spec_id}' not found"
        )

    success = file_manager.delete_workflow(spec_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow file"
        )

    return {"message": f"Workflow '{spec_id}' deleted successfully"}


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows() -> WorkflowListResponse:
    """
    List all stored workflows.
    """
    workflows = file_manager.list_workflows()
    storage_stats = file_manager.get_storage_stats()

    return WorkflowListResponse(
        workflows=workflows,
        total_count=len(workflows),
        storage_stats=storage_stats
    )


@router.post("/workflows/{spec_id}/validate")
async def validate_workflow(spec_id: str) -> Dict[str, Any]:
    """
    Validate an existing workflow's JSON structure.
    """
    workflow_data = file_manager.load_workflow(spec_id)

    if workflow_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with spec_id '{spec_id}' not found"
        )

    try:
        # Validate using Pydantic model
        WorkflowSpec(**workflow_data)
        return {
            "valid": True,
            "message": "Workflow JSON structure is valid",
            "spec_id": spec_id
        }
    except Exception as e:
        return {
            "valid": False,
            "message": "Workflow JSON structure is invalid",
            "error": str(e),
            "spec_id": spec_id
        }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    """
    storage_stats = file_manager.get_storage_stats()

    return {
        "status": "healthy",
        "service": "svc-builder",
        "version": "0.1.0",
        "storage": storage_stats
    }