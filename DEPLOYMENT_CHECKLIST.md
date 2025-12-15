# Phase 3 Deployment Checklist

## Pre-Deployment Steps

### Backend Setup

- [ ] **Install Dependencies**
  ```bash
  cd backend
  poetry install
  ```

- [ ] **Configure Anthropic API Key**
  - Option 1: Via Admin API
    ```bash
    curl -X POST http://localhost:8001/api/v1/admin/settings \
      -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "key": "anthropic_api_key",
        "value": "sk-ant-YOUR-KEY-HERE",
        "is_secret": true,
        "category": "api_tokens",
        "description": "Anthropic API key for Claude MCP integration"
      }'
    ```

  - Option 2: Via Environment Variable (will be encrypted on first use)
    ```bash
    # Add to backend/.env
    ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
    ```

- [ ] **Verify Database Migration**
  ```bash
  cd backend
  poetry run alembic current
  # Should show latest migration
  ```

- [ ] **Test MCP Server Import**
  ```bash
  cd backend
  python -c "from app.mcp_server.server import mcp_server; print('OK')"
  ```

- [ ] **Test API Routes**
  ```bash
  cd backend
  poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
  # Visit http://localhost:8001/api/docs
  # Verify /api/v1/ai/* endpoints appear
  ```

### Frontend Setup

- [ ] **Install Dependencies** (if not already done)
  ```bash
  cd frontend
  pnpm install
  ```

- [ ] **Verify TypeScript Compilation**
  ```bash
  cd frontend
  pnpm tsc --noEmit
  # Should have no errors
  ```

- [ ] **Test Dev Server**
  ```bash
  cd frontend
  pnpm dev
  # Visit http://localhost:3001
  ```

## Integration Steps

### 1. Update Scenario Studio Page

- [ ] **Import AI Components**
  ```typescript
  import { AIAssistantPanel } from '@/components/ai';
  import { useAIAssistantStore } from '@/stores/aiAssistantStore';
  ```

- [ ] **Add AI Button to Toolbar**
  ```typescript
  const { openPanel } = useAIAssistantStore();

  <Button
    type="primary"
    icon={<RobotOutlined />}
    onClick={() => openPanel(scenarioId)}
  >
    AI Assistant
  </Button>
  ```

- [ ] **Render AI Panel**
  ```typescript
  <AIAssistantPanel />
  ```

- [ ] **Add Cleanup on Unmount**
  ```typescript
  useEffect(() => {
    return () => {
      const { isOpen, closePanel } = useAIAssistantStore.getState();
      if (isOpen) {
        closePanel();
      }
    };
  }, []);
  ```

### 2. Test Basic Functionality

- [ ] **Create AI Session**
  1. Navigate to scenario editor
  2. Click "AI Assistant" button
  3. Verify panel opens
  4. Check browser console for session creation
  5. Verify green "Connected" indicator

- [ ] **Send Simple Message**
  1. Type "Hello" in chat input
  2. Click Send
  3. Verify message appears in chat
  4. Wait for AI response
  5. Verify response appears

- [ ] **Test Tool Call**
  1. Send message: "List my devices"
  2. Verify AI uses `list_devices` tool
  3. Check for tool call badge in message
  4. Expand tool call to see details

- [ ] **Test Validation**
  1. Send message: "Validate my scenario"
  2. Verify AI calls `validate_topology`
  3. Review validation results
  4. Check for warnings/issues

- [ ] **Test Auto-Addressing**
  1. Send message: "Auto-assign IP addresses"
  2. Verify AI calls `auto_assign_addresses`
  3. Refresh scenario to see updated IPs
  4. Verify devices have new IP addresses

- [ ] **Close Panel**
  1. Click X to close panel
  2. Verify session ends (check network tab)
  3. Verify panel closes cleanly

## Testing Checklist

### Functional Tests

- [ ] AI session lifecycle (create → chat → close)
- [ ] Message send/receive
- [ ] Tool execution (all 13 tools)
- [ ] Suggested prompts dropdown
- [ ] Accept/reject pending actions
- [ ] Error handling (network errors)
- [ ] Connection status indicator
- [ ] Message timestamps
- [ ] Tool call expansion
- [ ] Auto-scroll to latest message

### Edge Cases

- [ ] Send message while processing
- [ ] Close panel during AI response
- [ ] Multiple rapid messages
- [ ] Very long messages (500+ chars)
- [ ] Special characters in messages
- [ ] Empty scenario (no devices)
- [ ] Invalid scenario ID
- [ ] Missing API key
- [ ] Expired API key
- [ ] Network timeout

### Browser Compatibility

- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Chrome
- [ ] Mobile Safari

### Performance Tests

- [ ] Response time < 5s
- [ ] No memory leaks (open/close 10x)
- [ ] Smooth scrolling with 50+ messages
- [ ] Panel animation smooth
- [ ] No layout shift

## Security Checklist

- [ ] API key is encrypted in database
- [ ] API key not logged in console
- [ ] API key not in network responses
- [ ] Session validation working
- [ ] User can only access their scenarios
- [ ] XSS protection (test with `<script>alert('xss')</script>`)
- [ ] CSRF protection enabled
- [ ] Rate limiting considered

## Documentation

- [ ] Update README with AI features
- [ ] Add screenshots to docs
- [ ] Document supported prompts
- [ ] List all available tools
- [ ] Add troubleshooting guide
- [ ] Create video demo (optional)

## Monitoring

### Backend Logs

- [ ] AI session creation logs
- [ ] Tool execution logs
- [ ] Error logs
- [ ] API latency logs

### Frontend Logs

- [ ] Connection status changes
- [ ] Message send/receive
- [ ] Errors in console
- [ ] Performance metrics

### Metrics to Track

- [ ] Sessions per day
- [ ] Messages per session
- [ ] Tool calls per message
- [ ] Average response time
- [ ] Error rate
- [ ] User satisfaction (add feedback button)

## Production Readiness

### Backend

- [ ] **Use Redis for sessions**
  ```python
  # Replace in-memory sessions with Redis
  import redis
  r = redis.Redis(host='localhost', port=6379, db=0)
  ```

- [ ] **Add rate limiting**
  ```python
  from slowapi import Limiter
  limiter = Limiter(key_func=get_remote_address)

  @router.post("/chat")
  @limiter.limit("10/minute")
  async def chat_with_ai(...):
      ...
  ```

- [ ] **Enable HTTPS**
  - Update CORS origins
  - Update frontend API_URL

- [ ] **Add logging**
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.info("AI session created", extra={"session_id": session_id})
  ```

- [ ] **Monitor Anthropic usage**
  - Track token usage
  - Set budget alerts
  - Implement token limits per user

### Frontend

- [ ] **Error boundaries**
  ```typescript
  <ErrorBoundary fallback={<div>AI unavailable</div>}>
    <AIAssistantPanel />
  </ErrorBoundary>
  ```

- [ ] **Loading states**
  - Show skeleton while connecting
  - Disable input while processing
  - Show retry button on error

- [ ] **User feedback**
  ```typescript
  // Add thumbs up/down on messages
  <Space>
    <Button icon={<LikeOutlined />} />
    <Button icon={<DislikeOutlined />} />
  </Space>
  ```

## Rollback Plan

If issues arise:

1. **Disable AI Routes**
   ```python
   # In main.py, comment out:
   # app.include_router(ai.router, prefix=settings.api_prefix)
   # app.include_router(http_sse.router, prefix=settings.api_prefix)
   ```

2. **Hide AI Button**
   ```typescript
   // Conditional render
   {process.env.VITE_ENABLE_AI === 'true' && (
     <Button onClick={() => openPanel(scenarioId)}>AI Assistant</Button>
   )}
   ```

3. **Revert Dependencies**
   ```bash
   cd backend
   poetry remove anthropic
   git checkout HEAD -- pyproject.toml poetry.lock
   ```

## Post-Deployment

- [ ] Monitor error rates
- [ ] Check API usage/costs
- [ ] Collect user feedback
- [ ] Review logs for issues
- [ ] Plan improvements based on usage patterns

## Known Issues & Workarounds

### Issue: AI session timeout
**Workaround:** Implement heartbeat to keep session alive
```typescript
useEffect(() => {
  const interval = setInterval(() => {
    if (sessionId) {
      // Send heartbeat
    }
  }, 30000); // 30s
  return () => clearInterval(interval);
}, [sessionId]);
```

### Issue: Large scenarios slow to process
**Workaround:** Add scenario summary endpoint for AI context
```python
@router.get("/scenarios/{id}/summary")
async def get_summary(...):
    # Return only counts and stats, not full definition
    return {"device_count": 10, "flow_count": 15}
```

## Support Contacts

- **Backend Issues:** [Your backend team]
- **Frontend Issues:** [Your frontend team]
- **Anthropic API Issues:** support@anthropic.com
- **Infrastructure:** [Your DevOps team]

## Sign-off

- [ ] Backend Lead: _________________ Date: _______
- [ ] Frontend Lead: _________________ Date: _______
- [ ] QA Lead: _________________ Date: _______
- [ ] Product Owner: _________________ Date: _______

---

**Deployment Date:** _________________
**Deployed By:** _________________
**Version:** Phase 3 - AI Assistant Integration
