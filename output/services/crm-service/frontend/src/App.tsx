import React, { Suspense } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { AppRoutes } from './router';
import { AuthProvider } from './auth/AuthProvider';
import { NotificationProvider } from './contexts/NotificationContext';

/**
 * Error Boundary Component
 *
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI.
 *
 * @see https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary
 */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error to console in development
    console.error('Application error:', error);
    console.error('Error info:', errorInfo);
    // TODO: Send to error tracking service in production
  }

  override render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Box
          data-testid="error-boundary-container"
sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            p: 3,
            textAlign: 'center',
          }}        >
          <h1 data-testid="error-boundary-title">Something went wrong</h1>
          <p style={ { color: '#666', maxWidth: 500 }}>
            An unexpected error occurred. Please refresh the page or contact support if the
            problem persists.
          </p>
          <button
            data-testid="btn-error-refresh"
            onClick={() => window.location.reload()}
            style={ {
              marginTop: 16,
              padding: '8px 16px',
              backgroundColor: '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            Refresh Page
          </button>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <pre
              style={ {
                marginTop: 24,
                padding: 16,
                backgroundColor: '#f5f5f5',
                borderRadius: 4,
                overflow: 'auto',
                maxWidth: '100%',
                textAlign: 'left',
                fontSize: 12,
              }}
            >
              {this.state.error.toString()}
              {'\n'}
              {this.state.error.stack}
            </pre>
          )}
        </Box>
      );
    }

    return this.props.children;
  }
}

/**
 * Loading Fallback Component
 *
 * Displays a centered loading spinner while lazy-loaded
 * components or data are being fetched.
 */
const LoadingFallback: React.FC = () => (
  <Box
    data-testid="loading-fallback"
sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
    }}  >
    <CircularProgress data-testid="loading-spinner" />
  </Box>
);

/**
 * Material-UI Theme Configuration
 *
 * Defines the application's visual design system including colors,
 * typography, spacing, and component defaults.
 *
 * @see https://mui.com/material-ui/customization/theming/
 */
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: '2.5rem',
      fontWeight: 500,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 600,
            backgroundColor: '#f5f5f5',
          },
        },
      },
    },
  },
});

/**
 * Root Application Component
 *
 * Provides the application shell with:
 * - Material-UI theme configuration
 * - CSS baseline reset for consistent styling
 * - Error boundary for graceful error handling
 * - Suspense boundary for lazy-loaded components
 * - Router integration for navigation
 *
 * @description Root component for crm
 * @generated 2026-03-10T13:09:26.115903Z
 */
const App: React.FC = () => {
  return (
    <div data-testid="app-root">
      <ThemeProvider theme={ theme}>
        <CssBaseline />
        <NotificationProvider>
          <ErrorBoundary>
            <AuthProvider>
              <Suspense fallback={<LoadingFallback />}>
                <AppRoutes />
              </Suspense>
            </AuthProvider>
          </ErrorBoundary>
        </NotificationProvider>
      </ThemeProvider>
    </div>
  );
};

export default App;
