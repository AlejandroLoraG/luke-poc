"""
Health Monitoring Tools

This module provides tools for monitoring the health and status of the
workflow management system components, particularly the svc-builder service.
"""

from typing import Dict, Any, Optional
from svc_client import svc_client
from shared.schemas import StandardErrorResponse, ErrorCategory, ErrorSeverity, ErrorCodes
from config import settings


def create_success_response(data: Dict[str, Any], operation: str) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {"success": True, "operation": operation, "service": "mcp-server"}
    response.update(data)
    return response


def handle_tool_error(e: Exception, operation: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Handle tool errors with standardized error response."""
    return {
        "success": False,
        "error": str(e),
        "operation": operation,
        "service": "mcp-server",
        "context": context or {}
    }


async def check_svc_builder_health() -> Dict[str, Any]:
    """
    Check the health status of the svc-builder service.

    Returns:
        Health status and connection information
    """
    try:
        result = await svc_client.health_check()
        return create_success_response({
            "svc_builder_status": "healthy",
            "svc_builder_url": settings.svc_builder_url,
            "health_details": result
        }, "check_svc_builder_health")

    except Exception as e:
        return handle_tool_error(e, "check_svc_builder_health", {
            "svc_builder_status": "unhealthy",
            "svc_builder_url": settings.svc_builder_url
        })