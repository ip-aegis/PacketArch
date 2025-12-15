# Phase 3: MCP Server and AI Assistant Integration - Implementation Summary

## Overview
This document describes the implementation of Phase 3 for PacketArch OT Traffic Simulation Platform, which adds an MCP (Model Context Protocol) server and AI-driven scenario composition capabilities using Claude via Anthropic's API.

## Architecture

### Backend Components

#### 1. MCP Server Core (`backend/app/mcp_server/`)

**server.py** - Core MCP server implementation
- `MCPServer` class with tool and resource registry
- JSON-RPC 2.0 request/response handling
- Methods: `initialize`, `list_tools`, `call_tool`, `list_resources`, `read_resource`
- Global singleton instance `mcp_server`

**schemas/mcp_types.py** - MCP protocol types
- `JSONRPCRequest`, `JSONRPCResponse`, `JSONRPCError`
- `MCPCapabilities`, `MCPServerInfo`, `MCPInitializeResult`
- `ToolDefinition`, `ToolResult`, `ResourceDefinition`

#### 2. Data Sanitization (`backend/app/mcp_server/sanitization/`)

**sanitizer.py** - Anonymizes sensitive data before AI processing
- `DataSanitizer` class with IP/MAC/hostname mapping
- Uses RFC 5737 documentation IP ranges (192.0.2.x, 198.51.100.x, 203.0.113.x)
- Locally administered MAC addresses (02:00:00:xx:xx:xx)
- Generic hostname patterns (preserves device type prefix)

#### 3. AI Provider Integration (`backend/app/mcp_server/ai_providers/`)

**base.py** - Abstract AI provider interface
- `AIProvider` base class
- Methods: `chat()`, `stream_chat()`

**anthropic_provider.py** - Claude integration
- `AnthropicProvider` implementation
- Supports Claude Opus 4.5 model
- Converts MCP tools to Claude's format
- Handles tool_use blocks in responses
- Streaming support for real-time responses

#### 4. MCP Tools (`backend/app/mcp_server/tools/`)

**device_tools.py** - Device manipulation
- `list_devices` - List all devices in scenario
- `get_device` - Get device details
- `add_device` - Add device to scenario
- `update_device` - Update device properties
- `remove_device` - Remove device (and related flows)
- `suggest_device` - AI suggests device based on vertical/zone

**flow_tools.py** - Flow management
- `list_flows` - List all flows
- `get_flow` - Get flow details
- `add_flow` - Add flow with validation
- `update_flow` - Update flow properties
- `remove_flow` - Remove flow
- `suggest_flows` - AI suggests flows based on device types

**scenario_tools.py** - Scenario operations
- `get_scenario` - Get complete scenario data
- `get_scenario_summary` - Get statistics only
- `add_zone` - Add network zone
- `update_zone` - Update zone properties
- `add_phase` - Add simulation phase
- `generate_scenario` - AI generates complete scenario from scratch

**validation_tools.py** - Quality checks
- `validate_topology` - Check for orphaned devices, missing references, protocol mismatches
- `validate_addressing` - Check for IP/MAC conflicts
- `score_realism` - Score scenario 0-100 with factors
- `suggest_improvements` - AI suggests fixes

**addressing_tools.py** - Network addressing
- `auto_assign_addresses` - Auto-assign IPs/MACs (zone_based, sequential, vertical_based)
- `assign_device_address` - Set specific device network config
- `suggest_addressing_scheme` - AI suggests best scheme

#### 5. Transport Layer (`backend/app/mcp_server/transport/`)

**http_sse.py** - HTTP + Server-Sent Events transport
- `POST /mcp/message` - Send MCP request, get response
- `GET /mcp/events/{session_id}` - SSE stream for server messages
- `DELETE /mcp/sessions/{session_id}` - End session
- In-memory session storage (use Redis in production)

#### 6. AI API Routes (`backend/app/api/routes/ai.py`)

**Endpoints:**
- `POST /api/v1/ai/sessions` - Create new AI session
- `DELETE /api/v1/ai/sessions/{id}` - End session
- `POST /api/v1/ai/chat` - Send message, get AI response with tool calls
- `POST /api/v1/ai/actions/{id}/accept` - Execute proposed action
- `POST /api/v1/ai/actions/{id}/reject` - Reject proposed action
- `GET /api/v1/ai/tools` - List available tools

**Key Features:**
- Tool registration on session creation
- Retrieves encrypted Anthropic API key from system settings
- Builds context-aware system messages
- Handles tool execution results
- Manages pending actions

### Frontend Components

#### 1. State Management (`frontend/src/stores/`)

**aiAssistantStore.ts** - Zustand store for AI state
- State: `isOpen`, `isConnected`, `isProcessing`, `messages`, `pendingActions`
- Actions: `openPanel`, `closePanel`, `sendMessage`, `acceptAction`, `rejectAction`
- Integrated with AI API client
- Auto-creates/ends sessions

#### 2. API Client (`frontend/src/api/`)

**ai.ts** - AI assistant API client
- `createSession()` - Start new session
- `endSession()` - End session
- `sendMessage()` - Send chat message
- `acceptAction()` - Accept AI suggestion
- `rejectAction()` - Reject AI suggestion
- `getTools()` - Get available tools

#### 3. UI Components (`frontend/src/components/ai/`)

**AIAssistantPanel.tsx** - Main drawer component
- Collapsible right-side drawer
- Connection status indicator
- Pending actions badge
- Scrollable chat area
- Fixed input at bottom

**ChatInterface.tsx** - Message display
- Maps over messages array
- Displays user and assistant messages
- Shows pending suggestions
- Auto-scrolls to latest message
- Processing indicator

**ChatInput.tsx** - User input
- Multi-line text area with auto-resize
- Suggested prompts dropdown
- Enter to send, Shift+Enter for newline
- Disabled state handling

**MessageBubble.tsx** - Individual message
- User vs assistant styling
- Timestamp display
- Tool calls with expandable details
- JSON-formatted results

**SuggestionCard.tsx** - Action proposal
- Highlighted card for pending actions
- Description and parameters preview
- Accept/Reject buttons
- Visual distinction from chat messages

## Data Flow

### AI Chat Request Flow
1. User types message in ChatInput
2. aiAssistantStore.sendMessage() called
3. API POST to /api/v1/ai/chat with session_id, scenario_id, message
4. Backend validates session and scenario
5. Retrieves and decrypts Anthropic API key
6. Builds conversation context with system message
7. Registers MCP tools with server
8. Calls AnthropicProvider.chat() with tools
9. Claude may invoke tools (validate_topology, add_device, etc.)
10. Tools execute database operations
11. Results returned to Claude
12. Claude generates natural language response
13. Response sent back to frontend with tool_calls array
14. Message added to chat history
15. If actions pending, shown as SuggestionCard

### Tool Execution Flow
1. Claude decides to use a tool (e.g., "add_device")
2. Tool call routed through MCP server
3. Tool handler function called with arguments
4. Database operations performed (add device to scenario.definition)
5. Scenario version incremented
6. Changes committed to database
7. JSON result returned to Claude
8. Claude incorporates result into response

## Security Considerations

1. **API Key Encryption**: Anthropic API key stored encrypted using Fernet encryption
2. **Data Sanitization**: IP/MAC/hostname anonymization before sending to AI
3. **Session Validation**: All requests validate user ownership
4. **Tool Authorization**: Only authenticated users can invoke tools
5. **Input Validation**: Pydantic schemas on all API endpoints

## Database Schema Changes

No new tables required. Uses existing:
- `scenarios` table - stores scenario.definition JSON
- `system_settings` table - stores encrypted anthropic_api_key

## Configuration

### Backend
Add to `.env` or system settings:
```
# Anthropic API key (stored encrypted)
ANTHROPIC_API_KEY=sk-ant-...
```

### Frontend
No additional config needed. Uses existing API_URL.

## Installation

### Backend
```bash
cd backend
poetry add anthropic
poetry install
```

### Frontend
All dependencies already in package.json (zustand, axios, ant-design).

## Usage Example

### Python Tool Registration
```python
from app.mcp_server.server import mcp_server

mcp_server.register_tool(
    name="list_devices",
    description="List all devices in a scenario",
    input_schema={
        "type": "object",
        "properties": {
            "scenario_id": {"type": "string"}
        },
        "required": ["scenario_id"]
    },
    handler=lambda scenario_id: device_tools.list_devices(db, scenario_id)
)
```

### TypeScript Usage
```typescript
import { useAIAssistantStore } from '@/stores/aiAssistantStore';

function ScenarioStudio() {
  const { openPanel } = useAIAssistantStore();

  return (
    <Button onClick={() => openPanel(scenarioId)}>
      Open AI Assistant
    </Button>
  );
}
```

## Testing Checklist

- [ ] AI session creation/deletion
- [ ] Message sending and receiving
- [ ] Tool execution (add_device, add_flow, etc.)
- [ ] Validation tools (topology, addressing)
- [ ] Realism scoring
- [ ] Auto-addressing schemes
- [ ] Pending action accept/reject
- [ ] Error handling (missing API key, network errors)
- [ ] Data sanitization
- [ ] Session cleanup on disconnect

## Future Enhancements

1. **Streaming Responses**: Use SSE for real-time token streaming
2. **Redis Sessions**: Replace in-memory sessions with Redis
3. **Tool Result Caching**: Cache validation/scoring results
4. **Multi-turn Conversations**: Maintain conversation history across sessions
5. **Custom System Prompts**: Per-vertical AI personalities
6. **Voice Input**: Integrate speech-to-text
7. **Scenario Templates**: AI-generated starter templates
8. **Collaboration**: Multi-user AI sessions

## Files Created

### Backend (Python)
- `backend/app/mcp_server/__init__.py`
- `backend/app/mcp_server/server.py`
- `backend/app/mcp_server/schemas/__init__.py`
- `backend/app/mcp_server/schemas/mcp_types.py`
- `backend/app/mcp_server/sanitization/__init__.py`
- `backend/app/mcp_server/sanitization/sanitizer.py`
- `backend/app/mcp_server/ai_providers/__init__.py`
- `backend/app/mcp_server/ai_providers/base.py`
- `backend/app/mcp_server/ai_providers/anthropic_provider.py`
- `backend/app/mcp_server/tools/__init__.py`
- `backend/app/mcp_server/tools/device_tools.py`
- `backend/app/mcp_server/tools/flow_tools.py`
- `backend/app/mcp_server/tools/scenario_tools.py`
- `backend/app/mcp_server/tools/validation_tools.py`
- `backend/app/mcp_server/tools/addressing_tools.py`
- `backend/app/mcp_server/transport/__init__.py`
- `backend/app/mcp_server/transport/http_sse.py`
- `backend/app/api/routes/ai.py`

### Frontend (TypeScript/React)
- `frontend/src/stores/aiAssistantStore.ts`
- `frontend/src/api/ai.ts`
- `frontend/src/components/ai/index.ts`
- `frontend/src/components/ai/AIAssistantPanel.tsx`
- `frontend/src/components/ai/ChatInterface.tsx`
- `frontend/src/components/ai/ChatInput.tsx`
- `frontend/src/components/ai/MessageBubble.tsx`
- `frontend/src/components/ai/SuggestionCard.tsx`

### Modified Files
- `backend/app/main.py` - Added AI and MCP routes
- `backend/app/api/routes/__init__.py` - Exported ai module
- `backend/pyproject.toml` - Added anthropic dependency

## Summary

Phase 3 successfully implements a complete MCP server with AI-driven scenario composition. Users can now interact with Claude via a chat interface to:
- Inspect and modify scenarios
- Add/update/remove devices and flows
- Validate topology and addressing
- Score scenario realism
- Auto-assign network addresses
- Generate complete scenarios from scratch

The implementation uses industry best practices:
- Type-safe schemas with Pydantic
- Proper error handling
- Data sanitization for security
- Modular tool architecture
- Clean separation of concerns
- Comprehensive API documentation via OpenAPI/Swagger
