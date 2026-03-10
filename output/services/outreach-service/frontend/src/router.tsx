import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Layout from './layouts/Layout';
import { useAuth } from './auth/AuthProvider';

/**
 * Lazy-loaded page components
 *
 * Using React.lazy for code splitting to improve initial bundle size.
 * Each page is loaded on-demand when the route is accessed.
 *
 * @see https://react.dev/reference/react/lazy
 */
const HomePage = lazy(() => import('./pages/Home'));
const LoginPage = lazy(() => import('./pages/Login'));
const EmailAccountPage = lazy(() => import('./pages/EmailAccountPage'));
const EmailTemplatePage = lazy(() => import('./pages/EmailTemplatePage'));
const LifecycleEmailPage = lazy(() => import('./pages/LifecycleEmailPage'));
const MessagePage = lazy(() => import('./pages/MessagePage'));
const NotFoundPage = lazy(() => import('./pages/NotFound'));

/**
 * Loading Fallback Component
 *
 * Displays a centered loading spinner while lazy-loaded
 * page components are being fetched.
 */
const PageLoadingFallback: React.FC = () => (
  <Box
sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
    }}  >
    <CircularProgress />
  </Box>
);

/**
 * Protected Route Wrapper
 *
 * Redirects unauthenticated users to the login page.
 * Used to protect routes that require authentication.
 *
 * @param children - Child components to render if authenticated
 * @param redirectTo - Path to redirect to if not authenticated
 */
interface ProtectedRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  redirectTo = '/login',
}) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <Box
sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}      >
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
};

/**
 * Application Routes Component
 *
 * Defines all routes for the application using React Router.
 * Uses Routes/Route components for declarative routing.
 *
 * Route Structure:
 * - / (Home page)
 * - /email-accounts (EmailAccount list page)
 * - /email-templates (EmailTemplate list page)
 * - /lifecycle-emails (LifecycleEmail list page)
 * - /messages (Message list page)
 * - /* (404 Not Found)
 *
 * @see https://reactrouter.com/en/main/components/routes
 */
export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <Suspense fallback={<PageLoadingFallback />}>
            <LoginPage />
          </Suspense>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route
          index
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <HomePage />
            </Suspense>
          }
        />
        <Route
          path="email-accounts"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <EmailAccountPage />
            </Suspense>
          }
        />
        <Route
          path="email-templates"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <EmailTemplatePage />
            </Suspense>
          }
        />
        <Route
          path="lifecycle-emails"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <LifecycleEmailPage />
            </Suspense>
          }
        />
        <Route
          path="messages"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <MessagePage />
            </Suspense>
          }
        />
        <Route
          path="*"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <NotFoundPage />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
