# Chat Agent PoC - System Architecture

## 🏗️ Overview

The Chat Agent PoC is a conversational AI workflow management system built with a clean microservices architecture. The system enables users to create and manage business workflows through natural language conversations, automatically converting business requirements into technical workflow specifications using a JSON DSL.

## 🎯 Architecture Principles

- **Separation of Concerns**: Each service has a single, well-defined responsibility
- **Protocol-Based Integration**: Services communicate through standardized protocols (HTTP REST, MCP)
- **Type Safety**: Full Pydantic schema validation across all service boundaries
- **Business Language First**: AI maintains business terminology, never exposes technical implementation
- **Shared Component Reuse**: Common schemas, error handling, and configuration patterns

## 📊 System Architecture Diagram

```mermaid
graph TB
    subgraph "User Interface Layer"
        UI[Web Browser/cURL/REST Clients]
    end

    subgraph "AI Agent Service (Port 8001)"
        direction TB
        AIA[FastAPI Application]
        AIR[Chat & Workflow Routers]
        PAI[Pydantic AI Agent]
        GM[Google Gemini Integration]
        CM[Conversation Manager]
        SS[Streaming Service]
        WS[Workflow Storage]
        AIC[Config & Logging]
    end

    subgraph "MCP Server (Port 8002)"
        direction TB
        MCP[FastMCP Server]
        CO[Core Operations]
        WC[Workflow Creation]
        WU[Workflow Updates]
        WD[Workflow Discovery]
        SM[State Management]
        HM[Health Monitoring]
        SC[svc-builder Client]
    end

    subgraph "svc-builder Service (Port 8000)"
        direction TB
        SFA[FastAPI Application]
        WR[Workflow Router]
        FC[File CRUD Operations]
        FM[File Manager]
        VE[Validation Engine]
        SHC[Health Checks]
        SC2[Settings Config]
    end

    subgraph "Storage Layer"
        direction TB
        JSON[(JSON Workflow Files)]
        STOR["/storage/workflows/"]
    end

    subgraph "Shared Components"
        direction TB
        PS[Pydantic Schemas]
        ER[Error Response Standards]
        LOG[Structured Logging]
        CONF[Configuration Management]
    end

    subgraph "External Services"
        GEMINI[Google Gemini API]
    end

    %% User Interactions
    UI --> AIA

    %% AI Agent Internal
    AIA --> AIR
    AIR --> PAI
    PAI --> GM
    PAI --> CM
    AIA --> SS
    AIR --> WS
    AIA --> AIC

    %% AI Agent to MCP
    PAI --> MCP

    %% MCP Internal
    MCP --> CO
    MCP --> WC
    MCP --> WU
    MCP --> WD
    MCP --> SM
    MCP --> HM

    %% MCP to svc-builder
    CO --> SC
    WC --> SC
    WU --> SC
    WD --> SC
    SM --> SC
    SC --> SFA

    %% svc-builder Internal
    SFA --> WR
    WR --> FC
    FC --> FM
    WR --> VE
    SFA --> SHC
    SFA --> SC2

    %% Storage Access
    FM --> JSON
    JSON --> STOR

    %% External API
    GM --> GEMINI

    %% Shared Components Usage
    PS -.-> AIA
    PS -.-> MCP
    PS -.-> SFA
    ER -.-> AIA
    ER -.-> MCP
    ER -.-> SFA
    LOG -.-> AIC
    LOG -.-> MCP
    LOG -.-> SC2
    CONF -.-> AIC
    CONF -.-> MCP
    CONF -.-> SC2

    %% Styling
    classDef aiService fill:#e1f5fe
    classDef mcpService fill:#f3e5f5
    classDef svcService fill:#e8f5e8
    classDef storage fill:#fff3e0
    classDef shared fill:#fce4ec
    classDef external fill:#f1f8e9

    class AIA,AIR,PAI,GM,CM,SS,WS,AIC aiService
    class MCP,CO,WC,WU,WD,SM,HM,SC mcpService
    class SFA,WR,FC,FM,VE,SHC,SC2 svcService
    class JSON,STOR storage
    class PS,ER,LOG,CONF shared
    class GEMINI external
```

## 🔄 Request Flow Sequence

```mermaid
sequenceDiagram
    participant User
    participant AI as AI Agent (8001)
    participant MCP as MCP Server (8002)
    participant SVC as svc-builder (8000)
    participant Store as JSON Storage
    participant Gemini as Google Gemini API

    User->>AI: "Create a customer complaint workflow"

    Note over AI: Conversation Manager handles context
    AI->>Gemini: Process natural language with business context
    Gemini-->>AI: Structured business understanding

    Note over AI: Pydantic AI Agent determines workflow creation needed
    AI->>MCP: create_workflow_from_description(description)

    Note over MCP: Workflow Creation Tool processes request
    MCP->>SVC: POST /api/v1/workflows (WorkflowSpec)

    Note over SVC: Validation Engine validates schema
    SVC->>Store: Write JSON workflow file
    Store-->>SVC: Confirmation
    SVC-->>MCP: WorkflowSpec with generated IDs
    MCP-->>AI: Success response with workflow details

    Note over AI: Format business-friendly response
    AI-->>User: "Created 'Customer Complaint Handling' workflow with 3 states..."

    %% Error handling flow
    Note over AI,SVC: Error Handling (if validation fails)
    SVC->>SVC: StandardErrorResponse generated
    SVC-->>MCP: Structured error response
    MCP-->>AI: Tool error with business context
    AI->>AI: Convert to business language
    AI-->>User: "Let me adjust the workflow structure..."
```

## 🏢 Service Responsibilities

### 🤖 AI Agent Service (Port 8001)
**Role**: Conversational interface and business logic coordinator

**Core Responsibilities**:
- Natural language conversation management with users
- Integration with Google Gemini for AI processing
- Business workflow conceptualization and explanation
- MCP tool orchestration for workflow operations
- Streaming response support for real-time interactions
- In-memory conversation history management

**Key Components**:
- **Pydantic AI Agent**: Core conversational AI with business persona
- **Conversation Manager**: Context and history tracking
- **Streaming Service**: Real-time response delivery
- **Workflow Storage**: In-memory workflow caching
- **Error Handlers**: Business-friendly error conversion

**Technologies**: FastAPI, Pydantic AI, Google Gemini API, Python 3.10

---

### 🌉 MCP Server (Port 8002)
**Role**: Protocol bridge and workflow tool provider

**Core Responsibilities**:
- Model Context Protocol (MCP) server implementation
- Workflow management tool registration and execution
- Translation between AI Agent requests and svc-builder API
- Business logic abstraction for workflow operations
- Health monitoring and system diagnostics

**Tool Modules** (After Code Cleanup):
1. **Core Operations** (125 lines): CRUD, validation, listing
2. **Workflow Creation** (296 lines): Template-based and custom creation
3. **Workflow Updates** (307 lines): Structure and permission modifications
4. **Workflow Discovery** (213 lines): Search and exploration tools
5. **State Management** (183 lines): State and action management
6. **Health Monitoring** (35 lines): System health checks

**Technologies**: FastMCP, HTTP Client, Python 3.10

---

### 📁 svc-builder Service (Port 8000)
**Role**: JSON DSL file management and persistence

**Core Responsibilities**:
- JSON workflow file CRUD operations
- Pydantic schema validation and type safety
- File system management and organization
- Workflow specification persistence
- Data integrity and validation enforcement

**Key Components**:
- **File Manager**: JSON file operations with atomic writes
- **Validation Engine**: Multi-layer Pydantic validation
- **Workflow Router**: REST API endpoints
- **Health Checks**: Service availability monitoring
- **Error Handlers**: Standardized error response formatting

**Technologies**: FastAPI, Pydantic, File I/O, Python 3.10

## 🔗 Integration Architecture

### Protocol Stack
```mermaid
graph LR
    subgraph "Communication Protocols"
        HTTP[HTTP REST APIs]
        MCP[Model Context Protocol]
        JSON[JSON Data Exchange]
    end

    subgraph "Data Validation"
        PYDANTIC[Pydantic v2 Schemas]
        TYPE[Type Safety]
    end

    subgraph "Error Handling"
        STANDARD[StandardErrorResponse]
        BUSINESS[Business Language Conversion]
    end

    HTTP --> MCP
    MCP --> JSON
    JSON --> PYDANTIC
    PYDANTIC --> TYPE
    TYPE --> STANDARD
    STANDARD --> BUSINESS
```

### Network Architecture
```mermaid
graph TB
    subgraph "Docker Network: chat-agent-network"
        subgraph "ai-agent:8001"
            AI[AI Agent Service]
        end

        subgraph "mcp-server:8002"
            MCP[MCP Server]
        end

        subgraph "svc-builder:8000"
            SVC[svc-builder Service]
        end
    end

    subgraph "Host Network"
        HOST[localhost:8000, 8001, 8002]
    end

    subgraph "External"
        GEMINI[Google Gemini API]
        STORAGE[Host File System]
    end

    AI -->|http://mcp-server:8002| MCP
    MCP -->|http://svc-builder:8000| SVC
    AI -->|HTTPS| GEMINI
    SVC -->|File I/O| STORAGE

    HOST -.->|Port Mapping| AI
    HOST -.->|Port Mapping| MCP
    HOST -.->|Port Mapping| SVC
```

## 🛠️ Shared Component Architecture

### Shared Module Structure
```mermaid
graph TB
    subgraph "shared/ Module"
        subgraph "schemas/"
            WF[workflow.py]
            ERR[errors.py]
            INIT[__init__.py]
        end

        CONFIG[config.py]
        LOG[logging_config.py]
        SHARED_INIT[__init__.py]
    end

    subgraph "All Services Import"
        AI_SVC[ai-agent]
        MCP_SVC[mcp-server]
        SVC_SVC[svc-builder]
    end

    WF --> AI_SVC
    WF --> MCP_SVC
    WF --> SVC_SVC

    ERR --> AI_SVC
    ERR --> MCP_SVC
    ERR --> SVC_SVC

    CONFIG --> AI_SVC
    CONFIG --> MCP_SVC
    CONFIG --> SVC_SVC

    LOG --> AI_SVC
    LOG --> MCP_SVC
    LOG --> SVC_SVC
```

### Configuration Management
```mermaid
graph TB
    subgraph "shared/config.py"
        BASE[BaseServiceSettings]
        PORTS[ServicePorts]
        NAMES[ServiceNames]
        NETWORK[NetworkConfig]
        VALIDATE[validate_required_env_var]
    end

    subgraph "Service Configurations"
        AI_CONFIG[ai-agent/src/core/config.py]
        MCP_CONFIG[mcp-server/src/config.py]
        SVC_CONFIG[svc-builder/app/core/settings.py]
    end

    subgraph "Environment"
        ENV[.env file]
        DOCKER[Docker Compose ENV]
    end

    BASE --> AI_CONFIG
    BASE --> MCP_CONFIG
    BASE --> SVC_CONFIG

    PORTS --> AI_CONFIG
    PORTS --> MCP_CONFIG
    PORTS --> SVC_CONFIG

    ENV --> AI_CONFIG
    ENV --> MCP_CONFIG
    ENV --> SVC_CONFIG

    DOCKER --> AI_CONFIG
    DOCKER --> MCP_CONFIG
    DOCKER --> SVC_CONFIG
```

## 📦 Data Flow Architecture

### Workflow Creation Flow
```mermaid
flowchart TD
    START([User Request: Create Workflow]) --> PARSE[AI Agent Parses Natural Language]
    PARSE --> CONTEXT[Conversation Manager Adds Context]
    CONTEXT --> GEMINI[Google Gemini Processes Business Intent]
    GEMINI --> DECISION{Workflow Creation Needed?}

    DECISION -->|Yes| MCP_CALL[Call MCP create_workflow_from_description]
    DECISION -->|No| RESPONSE[Generate Informational Response]

    MCP_CALL --> TEMPLATE{Use Template?}
    TEMPLATE -->|Yes| LOAD_TEMPLATE[Load Workflow Template]
    TEMPLATE -->|No| CUSTOM[Create Custom Workflow Structure]

    LOAD_TEMPLATE --> CUSTOMIZE[Customize Template with User Requirements]
    CUSTOM --> VALIDATE_SCHEMA[Validate WorkflowSpec Schema]
    CUSTOMIZE --> VALIDATE_SCHEMA

    VALIDATE_SCHEMA --> API_CALL[POST to svc-builder /workflows]
    API_CALL --> VALIDATION[svc-builder Validates & Stores]
    VALIDATION --> STORAGE[Write JSON to File System]

    STORAGE --> SUCCESS[Return WorkflowSpec with IDs]
    SUCCESS --> FORMAT[AI Agent Formats Business Response]
    RESPONSE --> FORMAT
    FORMAT --> END([Return to User])

    %% Error Paths
    VALIDATION -->|Error| ERROR_HANDLER[StandardErrorResponse]
    ERROR_HANDLER --> BUSINESS_ERROR[Convert to Business Language]
    BUSINESS_ERROR --> END
```

### Error Handling Flow
```mermaid
flowchart TD
    ERROR[Error Occurs in Any Service] --> DETECT[Error Detection]
    DETECT --> TYPE{Error Type?}

    TYPE -->|Validation| VALIDATION_ERROR[ValidationErrorResponse]
    TYPE -->|Not Found| NOTFOUND_ERROR[NotFoundErrorResponse]
    TYPE -->|Internal| INTERNAL_ERROR[InternalErrorResponse]
    TYPE -->|External| EXTERNAL_ERROR[ExternalServiceErrorResponse]

    VALIDATION_ERROR --> STANDARD[StandardErrorResponse Format]
    NOTFOUND_ERROR --> STANDARD
    INTERNAL_ERROR --> STANDARD
    EXTERNAL_ERROR --> STANDARD

    STANDARD --> LOG[Structured Logging]
    LOG --> PROPAGATE[Propagate Through Service Chain]
    PROPAGATE --> AI_CONVERT[AI Agent Converts to Business Language]
    AI_CONVERT --> USER_RESPONSE[User-Friendly Error Message]
```

## 🧪 Testing Architecture

### Test Strategy Overview
```mermaid
graph TB
    subgraph "Testing Levels"
        UNIT[Unit Tests - Each Service]
        INTEGRATION[Integration Tests - Service Communication]
        E2E[End-to-End Tests - Full User Scenarios]
        PERSONA[Persona Tests - Realistic User Behavior]
    end

    subgraph "Test Tools"
        PYTEST[pytest - Unit Testing]
        DOCKER[Docker Compose - Integration Environment]
        CURL[cURL Scripts - API Testing]
        BASH[Bash Scripts - Automated Scenarios]
    end

    subgraph "Test Coverage"
        SERVICES[All Service Endpoints]
        WORKFLOWS[Workflow CRUD Operations]
        CONVERSATION[Conversational AI Behavior]
        ERROR[Error Handling Scenarios]
    end

    UNIT --> PYTEST
    INTEGRATION --> DOCKER
    E2E --> CURL
    PERSONA --> BASH

    PYTEST --> SERVICES
    DOCKER --> WORKFLOWS
    CURL --> CONVERSATION
    BASH --> ERROR
```

## 🚀 Deployment Architecture

### Container Orchestration
```mermaid
graph TB
    subgraph "Docker Compose Stack"
        subgraph "Services"
            AI_CONTAINER[ai-agent Container]
            MCP_CONTAINER[mcp-server Container]
            SVC_CONTAINER[svc-builder Container]
        end

        subgraph "Networking"
            NETWORK[chat-agent-network Bridge]
        end

        subgraph "Storage"
            VOLUMES[Docker Volumes]
            HOST_STORAGE[Host File System Mounts]
        end

        subgraph "Health Monitoring"
            HEALTHCHECKS[Service Health Checks]
            DEPENDENCIES[Service Dependencies]
        end
    end

    AI_CONTAINER --> NETWORK
    MCP_CONTAINER --> NETWORK
    SVC_CONTAINER --> NETWORK

    SVC_CONTAINER --> VOLUMES
    VOLUMES --> HOST_STORAGE

    AI_CONTAINER --> HEALTHCHECKS
    MCP_CONTAINER --> HEALTHCHECKS
    SVC_CONTAINER --> HEALTHCHECKS

    HEALTHCHECKS --> DEPENDENCIES
```

## 📈 Performance Characteristics

### System Metrics
- **Service Startup Time**: ~10-15 seconds (full stack)
- **API Response Time**: <200ms (typical workflow operations)
- **Concurrent Conversations**: Supported (stateless design)
- **Memory Footprint**: ~300MB total (all services)
- **Storage Efficiency**: JSON files, ~2-5KB per workflow

### Scalability Considerations
- **Horizontal Scaling**: Each service can be scaled independently
- **State Management**: Conversations stored in-memory (session-based)
- **Database Ready**: File storage easily replaceable with database
- **Load Balancing**: FastAPI services are load balancer compatible

## 🔒 Security Architecture

### Security Layers
```mermaid
graph TB
    subgraph "Security Measures"
        subgraph "API Security"
            CORS[CORS Configuration]
            VALIDATION[Input Validation]
            RATE_LIMIT[Rate Limiting Ready]
        end

        subgraph "Data Security"
            SCHEMA_VAL[Schema Validation]
            FILE_PERM[File Permissions]
            NO_SECRETS[No Hardcoded Secrets]
        end

        subgraph "Network Security"
            DOCKER_NET[Isolated Docker Network]
            PORT_CONTROL[Controlled Port Exposure]
            API_KEYS[External API Key Management]
        end
    end
```

## 🎯 Code Quality Achievements

### Recent Improvements (Code Cleanup Phase)
1. **Eliminated sys.path.append() hacks** - Proper Python package structure
2. **Modular MCP Server** - Split 1169 lines into 6 organized modules (~150-300 lines each)
3. **Standardized Error Handling** - Consistent error responses across all services
4. **Shared Configuration Management** - Centralized settings with validation
5. **Structured Logging Framework** - JSON logging for observability
6. **Type Safety** - Full Pydantic v2 compatibility throughout

### Architecture Quality Metrics
- **Separation of Concerns**: ✅ Each service has single responsibility
- **DRY Principle**: ✅ Shared components eliminate duplication
- **Type Safety**: ✅ End-to-end Pydantic validation
- **Error Handling**: ✅ Standardized error responses
- **Testability**: ✅ Clean interfaces and dependency injection
- **Maintainability**: ✅ Modular structure with clear boundaries

---

This architecture supports the current PoC requirements while providing a solid foundation for scaling to a production MVP with features like real-time streaming, enhanced UI integration, and workflow execution capabilities.