import React, { Suspense } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { AppRoutes } from './router';
import { AuthProvider } from './auth/AuthProvider';
import { NotificationProvider } from './contexts/NotificationContext';
import { venturestratTheme } from './theme';

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  override componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Application error:', error, info);
  }
  override render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', p: 3, textAlign: 'center', bgcolor: '#f9fafb', color: '#374151' }}>
          <h1>Something went wrong</h1>
          <p style={{ color: '#6b7280', maxWidth: 500 }}>An unexpected error occurred. Please refresh the page.</p>
          <button onClick={() => window.location.reload()} style={{ marginTop: 16, padding: '8px 16px', backgroundColor: '#e5e7eb', color: '#4f7df9', border: '1px solid #4f7df9', borderRadius: 4, cursor: 'pointer' }}>
            Refresh Page
          </button>
        </Box>
      );
    }
    return this.props.children;
  }
}

const App: React.FC = () => (
  <ThemeProvider theme={venturestratTheme}>
    <CssBaseline />
    <NotificationProvider>
      <ErrorBoundary>
        <AuthProvider>
          <Suspense fallback={<Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', bgcolor: '#f9fafb' }}><CircularProgress sx={{ color: '#4f7df9' }} /></Box>}>
            <AppRoutes />
          </Suspense>
        </AuthProvider>
      </ErrorBoundary>
    </NotificationProvider>
  </ThemeProvider>
);

export default App;
