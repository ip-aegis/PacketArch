import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntApp, theme as antTheme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';

// Create a client for TanStack Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Cisco-inspired Ant Design theme configuration
const theme = {
  token: {
    // Cisco brand colors
    colorPrimary: '#049FD9',           // Cisco Blue
    colorInfo: '#049FD9',
    colorSuccess: '#6CC04A',           // Cisco Green
    colorWarning: '#FFCC00',           // Cisco Yellow
    colorError: '#CF2030',             // Cisco Red
    colorLink: '#00BCEB',              // Cisco Cyan

    // Dark theme base
    colorBgBase: '#1a1a2e',
    colorTextBase: '#ffffff',

    // Component styling
    borderRadius: 4,
    fontFamily: '"CiscoSans", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: {
      headerBg: '#0d0d1a',
      siderBg: '#141428',
      bodyBg: '#1a1a2e',
    },
    Menu: {
      darkItemBg: '#141428',
      darkItemSelectedBg: '#049FD9',
      darkItemHoverBg: '#1f1f3d',
    },
    Card: {
      colorBgContainer: '#232342',
      colorBorderSecondary: '#2d2d52',
    },
    Button: {
      primaryShadow: '0 2px 8px rgba(4, 159, 217, 0.35)',
    },
    Input: {
      colorBgContainer: '#232342',
      colorBorder: '#3d3d6b',
      activeBorderColor: '#049FD9',
      hoverBorderColor: '#00BCEB',
    },
    Table: {
      colorBgContainer: '#232342',
      headerBg: '#1a1a2e',
      rowHoverBg: '#2d2d52',
    },
  },
  algorithm: antTheme.darkAlgorithm,
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider theme={theme}>
          <AntApp>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </AntApp>
        </ConfigProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>
);
