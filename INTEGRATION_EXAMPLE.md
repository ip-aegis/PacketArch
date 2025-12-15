# AI Assistant Integration Example

This document shows how to integrate the AI Assistant Panel into your scenario editor page.

## Basic Integration

### 1. Import the Components

```typescript
import { AIAssistantPanel } from '@/components/ai';
import { useAIAssistantStore } from '@/stores/aiAssistantStore';
```

### 2. Add to Your Scenario Page

```typescript
import React, { useEffect } from 'react';
import { Button, Space } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import { AIAssistantPanel } from '@/components/ai';
import { useAIAssistantStore } from '@/stores/aiAssistantStore';

interface ScenarioStudioPageProps {
  scenarioId: string;
}

const ScenarioStudioPage: React.FC<ScenarioStudioPageProps> = ({ scenarioId }) => {
  const { isOpen, openPanel, closePanel } = useAIAssistantStore();

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (isOpen) {
        closePanel();
      }
    };
  }, [isOpen, closePanel]);

  const handleOpenAI = () => {
    openPanel(scenarioId);
  };

  return (
    <div style={{ position: 'relative', height: '100vh' }}>
      {/* Your existing scenario editor UI */}
      <div style={{ padding: 24 }}>
        <Space>
          <h1>Scenario Editor</h1>

          {/* AI Assistant Toggle Button */}
          <Button
            type="primary"
            icon={<RobotOutlined />}
            onClick={handleOpenAI}
            disabled={isOpen}
          >
            AI Assistant
          </Button>
        </Space>

        {/* Your canvas, device list, etc. */}
        <div className="scenario-canvas">
          {/* ... */}
        </div>
      </div>

      {/* AI Assistant Panel (renders as a drawer) */}
      <AIAssistantPanel />
    </div>
  );
};

export default ScenarioStudioPage;
```

## Advanced: Listening for AI Actions

If you need to react when AI makes changes to the scenario (e.g., refresh the canvas):

```typescript
import { useEffect } from 'react';
import { useAIAssistantStore } from '@/stores/aiAssistantStore';

const ScenarioStudioPage: React.FC<ScenarioStudioPageProps> = ({ scenarioId }) => {
  const { messages } = useAIAssistantStore();

  // Watch for new messages that might indicate changes
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];

    if (lastMessage?.role === 'assistant' && lastMessage.toolCalls) {
      // AI used tools - might need to refresh scenario
      console.log('AI used tools:', lastMessage.toolCalls);

      // Refresh your scenario data
      refetchScenario();
    }
  }, [messages]);

  const refetchScenario = () => {
    // Your logic to reload scenario from API
  };

  // ... rest of component
};
```

## Floating Action Button Style

For a floating button in the corner:

```typescript
import { FloatButton } from 'antd';
import { RobotOutlined } from '@ant-design/icons';

const ScenarioStudioPage: React.FC<ScenarioStudioPageProps> = ({ scenarioId }) => {
  const { isOpen, openPanel } = useAIAssistantStore();

  return (
    <>
      {/* Your page content */}
      <div>{/* ... */}</div>

      {/* Floating AI Button */}
      {!isOpen && (
        <FloatButton
          icon={<RobotOutlined />}
          type="primary"
          style={{ right: 24, bottom: 24 }}
          onClick={() => openPanel(scenarioId)}
          tooltip="AI Assistant"
        />
      )}

      {/* AI Panel */}
      <AIAssistantPanel />
    </>
  );
};
```

## Example Toolbar Integration

If you have a toolbar:

```typescript
import { Button, Space, Divider } from 'antd';
import { SaveOutlined, PlayCircleOutlined, RobotOutlined } from '@ant-design/icons';

const ScenarioToolbar: React.FC = () => {
  const { openPanel } = useAIAssistantStore();
  const scenarioId = useScenarioId(); // Your hook

  return (
    <Space split={<Divider type="vertical" />}>
      <Button icon={<SaveOutlined />}>Save</Button>
      <Button icon={<PlayCircleOutlined />}>Run Simulation</Button>

      {/* AI Assistant */}
      <Button
        type="primary"
        icon={<RobotOutlined />}
        onClick={() => openPanel(scenarioId)}
      >
        AI Help
      </Button>
    </Space>
  );
};
```

## Customizing the Panel

The AI Assistant Panel is built with Ant Design and supports theming. You can wrap it with a ConfigProvider:

```typescript
import { ConfigProvider } from 'antd';

<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#1890ff',
      // ... your theme tokens
    },
  }}
>
  <AIAssistantPanel />
</ConfigProvider>
```

## Error Handling

The store handles errors internally, but you can add toast notifications:

```typescript
import { message } from 'antd';
import { useEffect } from 'react';
import { useAIAssistantStore } from '@/stores/aiAssistantStore';

const ScenarioStudioPage: React.FC = () => {
  const { isConnected, messages } = useAIAssistantStore();

  useEffect(() => {
    if (!isConnected) {
      message.warning('AI Assistant disconnected. Please check your API key configuration.');
    }
  }, [isConnected]);

  // Show error messages
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];

    if (lastMessage?.content.includes('error')) {
      message.error('AI encountered an error');
    }
  }, [messages]);

  // ...
};
```

## Full Example with React Router

```typescript
// pages/ScenarioStudioPage.tsx
import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Layout, Button, Space } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import { AIAssistantPanel } from '@/components/ai';
import { useAIAssistantStore } from '@/stores/aiAssistantStore';

const { Header, Content } = Layout;

const ScenarioStudioPage: React.FC = () => {
  const { id: scenarioId } = useParams<{ id: string }>();
  const { isOpen, openPanel, closePanel } = useAIAssistantStore();

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (isOpen) {
        closePanel();
      }
    };
  }, [isOpen, closePanel]);

  if (!scenarioId) {
    return <div>Scenario not found</div>;
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px' }}>
        <Space>
          <h1>Scenario Studio</h1>
          <Button
            type="primary"
            icon={<RobotOutlined />}
            onClick={() => openPanel(scenarioId)}
            disabled={isOpen}
          >
            AI Assistant
          </Button>
        </Space>
      </Header>

      <Content style={{ padding: 24 }}>
        {/* Your scenario editor */}
        <div className="scenario-canvas">
          {/* Canvas, device list, flow diagram, etc. */}
        </div>
      </Content>

      {/* AI Assistant Panel */}
      <AIAssistantPanel />
    </Layout>
  );
};

export default ScenarioStudioPage;
```

## API Usage

You can also use the AI API directly:

```typescript
import { aiApi } from '@/api/ai';

// Create session
const session = await aiApi.createSession();

// Send message
const response = await aiApi.sendMessage({
  session_id: session.session_id,
  scenario_id: scenarioId,
  message: 'Add a PLC to the plant floor',
});

console.log('AI Response:', response.response);
console.log('Tool Calls:', response.tool_calls);

// Clean up
await aiApi.endSession(session.session_id);
```

## Testing

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { useAIAssistantStore } from '@/stores/aiAssistantStore';
import ScenarioStudioPage from './ScenarioStudioPage';

describe('AI Assistant Integration', () => {
  it('opens AI panel when button clicked', () => {
    const { openPanel } = useAIAssistantStore.getState();

    render(<ScenarioStudioPage scenarioId="test-id" />);

    const button = screen.getByText('AI Assistant');
    fireEvent.click(button);

    expect(useAIAssistantStore.getState().isOpen).toBe(true);
  });
});
```

## Next Steps

1. Configure Anthropic API key in system settings
2. Add AI button to your scenario editor
3. Test with simple prompts like "Validate my scenario"
4. Explore advanced features (auto-addressing, flow suggestions)
5. Customize the UI to match your theme
