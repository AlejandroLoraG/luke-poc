from typing import Dict, Any

# Sample workflow definitions for testing and development
SAMPLE_WORKFLOWS: Dict[str, Dict[str, Any]] = {
    "wf_incidentes": {
        "specId": "wf_incidentes",
        "specVersion": 1,
        "tenantId": "luke_123",
        "name": "Gestión de Incidentes",
        "slug": "gestion_incidentes",
        "states": [
            {"slug": "reportado", "name": "Incidente reportado", "type": "initial"},
            {"slug": "en_resolucion", "name": "En resolución", "type": "intermediate"},
            {"slug": "resuelto", "name": "Resuelto", "type": "final"}
        ],
        "actions": [
            {
                "slug": "pasar_a_resolucion",
                "from": "reportado",
                "to": "en_resolucion",
                "requiresForm": False,
                "permission": "pasar_a_resolucion"
            },
            {
                "slug": "resolver_incidencia",
                "from": "en_resolucion",
                "to": "resuelto",
                "requiresForm": True,
                "permission": "resolver_incidencia",
                "form": {
                    "name": "Resolver incidencia",
                    "fields": [
                        {
                            "key": "diagnostico_final",
                            "type": "string",
                            "required": True
                        },
                        {
                            "key": "fecha_resolucion",
                            "type": "date",
                            "required": True
                        }
                    ]
                }
            }
        ],
        "permissions": [
            {"slug": "pasar_a_resolucion"},
            {"slug": "resolver_incidencia"}
        ],
        "automations": [
            {
                "slug": "notify_twilio_on_resuelto",
                "on": {
                    "event": "task.state.changed",
                    "to": "resuelto"
                },
                "effect": {
                    "type": "twilio.notify.subscribers",
                    "params": {
                        "template": "resuelto_tpl_v1"
                    }
                }
            }
        ]
    },

    "wf_approval": {
        "specId": "wf_approval",
        "specVersion": 1,
        "tenantId": "luke_123",
        "name": "Document Approval",
        "slug": "document_approval",
        "states": [
            {"slug": "draft", "name": "Draft", "type": "initial"},
            {"slug": "pending_review", "name": "Pending Review", "type": "intermediate"},
            {"slug": "approved", "name": "Approved", "type": "final"},
            {"slug": "rejected", "name": "Rejected", "type": "final"}
        ],
        "actions": [
            {
                "slug": "submit_for_review",
                "from": "draft",
                "to": "pending_review",
                "requiresForm": False,
                "permission": "submit_document"
            },
            {
                "slug": "approve_document",
                "from": "pending_review",
                "to": "approved",
                "requiresForm": True,
                "permission": "approve_document",
                "form": {
                    "name": "Approval Form",
                    "fields": [
                        {
                            "key": "approval_comments",
                            "type": "string",
                            "required": False
                        },
                        {
                            "key": "approved_by",
                            "type": "string",
                            "required": True
                        }
                    ]
                }
            },
            {
                "slug": "reject_document",
                "from": "pending_review",
                "to": "rejected",
                "requiresForm": True,
                "permission": "approve_document",
                "form": {
                    "name": "Rejection Form",
                    "fields": [
                        {
                            "key": "rejection_reason",
                            "type": "string",
                            "required": True
                        }
                    ]
                }
            }
        ],
        "permissions": [
            {"slug": "submit_document"},
            {"slug": "approve_document"}
        ],
        "automations": [
            {
                "slug": "notify_on_approval",
                "on": {
                    "event": "task.state.changed",
                    "to": "approved"
                },
                "effect": {
                    "type": "email.notify",
                    "params": {
                        "template": "approval_notification"
                    }
                }
            }
        ]
    },

    "wf_tasks": {
        "specId": "wf_tasks",
        "specVersion": 1,
        "tenantId": "luke_123",
        "name": "Task Management",
        "slug": "task_management",
        "states": [
            {"slug": "todo", "name": "To Do", "type": "initial"},
            {"slug": "in_progress", "name": "In Progress", "type": "intermediate"},
            {"slug": "review", "name": "In Review", "type": "intermediate"},
            {"slug": "done", "name": "Done", "type": "final"},
            {"slug": "cancelled", "name": "Cancelled", "type": "final"}
        ],
        "actions": [
            {
                "slug": "start_task",
                "from": "todo",
                "to": "in_progress",
                "requiresForm": False,
                "permission": "manage_tasks"
            },
            {
                "slug": "submit_for_review",
                "from": "in_progress",
                "to": "review",
                "requiresForm": True,
                "permission": "manage_tasks",
                "form": {
                    "name": "Task Completion",
                    "fields": [
                        {
                            "key": "completion_notes",
                            "type": "string",
                            "required": True
                        },
                        {
                            "key": "time_spent",
                            "type": "number",
                            "required": False
                        }
                    ]
                }
            },
            {
                "slug": "approve_task",
                "from": "review",
                "to": "done",
                "requiresForm": False,
                "permission": "approve_tasks"
            },
            {
                "slug": "request_changes",
                "from": "review",
                "to": "in_progress",
                "requiresForm": True,
                "permission": "approve_tasks",
                "form": {
                    "name": "Request Changes",
                    "fields": [
                        {
                            "key": "change_requests",
                            "type": "string",
                            "required": True
                        }
                    ]
                }
            },
            {
                "slug": "cancel_task",
                "from": "todo",
                "to": "cancelled",
                "requiresForm": True,
                "permission": "manage_tasks",
                "form": {
                    "name": "Cancel Task",
                    "fields": [
                        {
                            "key": "cancellation_reason",
                            "type": "string",
                            "required": True
                        }
                    ]
                }
            },
            {
                "slug": "cancel_from_progress",
                "from": "in_progress",
                "to": "cancelled",
                "requiresForm": True,
                "permission": "manage_tasks",
                "form": {
                    "name": "Cancel Task",
                    "fields": [
                        {
                            "key": "cancellation_reason",
                            "type": "string",
                            "required": True
                        }
                    ]
                }
            }
        ],
        "permissions": [
            {"slug": "manage_tasks"},
            {"slug": "approve_tasks"}
        ],
        "automations": [
            {
                "slug": "notify_on_completion",
                "on": {
                    "event": "task.state.changed",
                    "to": "done"
                },
                "effect": {
                    "type": "slack.notify",
                    "params": {
                        "channel": "#tasks",
                        "template": "task_completed"
                    }
                }
            }
        ]
    }
}