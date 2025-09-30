from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from shared.schemas import WorkflowSpec
from ..core.workflow_storage import workflow_storage

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


class WorkflowCreateRequest(BaseModel):
    workflow_id: Optional[str] = None
    workflow_spec: WorkflowSpec


class WorkflowUpdateRequest(BaseModel):
    workflow_spec: WorkflowSpec


class WorkflowListResponse(BaseModel):
    workflows: List[Dict[str, Any]]
    total_count: int
    stats: Dict[str, Any]


@router.post("/", status_code=201)
async def create_workflow(request: WorkflowCreateRequest) -> Dict[str, Any]:
    """
    Store a new workflow in memory.
    """
    # Use provided workflow_id or extract from spec
    workflow_id = request.workflow_id or request.workflow_spec.spec_id

    if not workflow_id:
        raise HTTPException(
            status_code=400,
            detail="Workflow ID must be provided either directly or in workflow_spec.specId"
        )

    # Convert WorkflowSpec to dict
    workflow_data = request.workflow_spec.model_dump()

    # Check if workflow already exists
    if workflow_storage.workflow_exists(workflow_id):
        raise HTTPException(
            status_code=409,
            detail=f"Workflow with ID '{workflow_id}' already exists. Use PUT to update."
        )

    # Store the workflow
    success = workflow_storage.store_workflow(workflow_id, workflow_data)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to store workflow"
        )

    return {
        "message": "Workflow created successfully",
        "workflow_id": workflow_id,
        "spec_id": workflow_data.get("specId"),
        "name": workflow_data.get("name")
    }


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    include_samples: bool = Query(True, description="Include sample workflows in results")
) -> WorkflowListResponse:
    """
    List all stored workflows.
    """
    workflows = workflow_storage.list_workflows()

    # Filter samples if requested
    if not include_samples:
        workflows = [wf for wf in workflows if not wf.get("is_sample", False)]

    stats = workflow_storage.get_stats()

    return WorkflowListResponse(
        workflows=workflows,
        total_count=len(workflows),
        stats=stats
    )


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific workflow by ID.
    """
    workflow_data = workflow_storage.get_workflow(workflow_id)

    if workflow_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow with ID '{workflow_id}' not found"
        )

    metadata = workflow_storage.get_workflow_metadata(workflow_id)

    return {
        "workflow_id": workflow_id,
        "workflow_spec": workflow_data,
        "metadata": metadata
    }


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, request: WorkflowUpdateRequest) -> Dict[str, Any]:
    """
    Update an existing workflow.
    """
    if not workflow_storage.workflow_exists(workflow_id):
        raise HTTPException(
            status_code=404,
            detail=f"Workflow with ID '{workflow_id}' not found"
        )

    # Convert WorkflowSpec to dict
    workflow_data = request.workflow_spec.model_dump()

    # Update the workflow
    success = workflow_storage.update_workflow(workflow_id, workflow_data)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to update workflow"
        )

    return {
        "message": "Workflow updated successfully",
        "workflow_id": workflow_id,
        "spec_id": workflow_data.get("specId"),
        "name": workflow_data.get("name")
    }


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, str]:
    """
    Delete a workflow from storage.
    """
    if not workflow_storage.workflow_exists(workflow_id):
        raise HTTPException(
            status_code=404,
            detail=f"Workflow with ID '{workflow_id}' not found"
        )

    # Check if it's a sample workflow
    metadata = workflow_storage.get_workflow_metadata(workflow_id)
    if metadata and metadata.get("is_sample", False):
        raise HTTPException(
            status_code=403,
            detail="Cannot delete sample workflows"
        )

    success = workflow_storage.delete_workflow(workflow_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete workflow"
        )

    return {"message": f"Workflow '{workflow_id}' deleted successfully"}


@router.post("/{workflow_id}/duplicate")
async def duplicate_workflow(
    workflow_id: str,
    new_workflow_id: str = Query(..., description="ID for the duplicated workflow")
) -> Dict[str, Any]:
    """
    Duplicate an existing workflow with a new ID.
    """
    original_workflow = workflow_storage.get_workflow(workflow_id)

    if original_workflow is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow with ID '{workflow_id}' not found"
        )

    if workflow_storage.workflow_exists(new_workflow_id):
        raise HTTPException(
            status_code=409,
            detail=f"Workflow with ID '{new_workflow_id}' already exists"
        )

    # Create a copy and update the IDs
    new_workflow = original_workflow.copy()
    new_workflow["specId"] = new_workflow_id

    # Store the duplicated workflow
    success = workflow_storage.store_workflow(new_workflow_id, new_workflow)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to duplicate workflow"
        )

    return {
        "message": "Workflow duplicated successfully",
        "original_workflow_id": workflow_id,
        "new_workflow_id": new_workflow_id,
        "name": new_workflow.get("name")
    }


@router.delete("/")
async def clear_all_workflows(
    keep_samples: bool = Query(True, description="Keep sample workflows")
) -> Dict[str, Any]:
    """
    Clear all workflows from storage.
    """
    stats_before = workflow_storage.get_stats()
    workflow_storage.clear_all_workflows(keep_samples=keep_samples)
    stats_after = workflow_storage.get_stats()

    return {
        "message": "Workflows cleared successfully",
        "keep_samples": keep_samples,
        "workflows_before": stats_before["total_workflows"],
        "workflows_after": stats_after["total_workflows"]
    }