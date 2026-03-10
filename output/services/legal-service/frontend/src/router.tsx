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
const ContactPersonPage = lazy(() => import('./pages/ContactPersonPage'));
const DocumentPartyPage = lazy(() => import('./pages/DocumentPartyPage'));
const DocumentTemplatePage = lazy(() => import('./pages/DocumentTemplatePage'));
const EquityGrantPage = lazy(() => import('./pages/EquityGrantPage'));
const InvestmentTermPage = lazy(() => import('./pages/InvestmentTermPage'));
const LegalAddressPage = lazy(() => import('./pages/LegalAddressPage'));
const LegalDocumentPage = lazy(() => import('./pages/LegalDocumentPage'));
const LegalEntityPage = lazy(() => import('./pages/LegalEntityPage'));
const TemplateClausePage = lazy(() => import('./pages/TemplateClausePage'));
const VestingSchedulePage = lazy(() => import('./pages/VestingSchedulePage'));
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
 * - /contact-persons (ContactPerson list page)
 * - /document-parties (DocumentParty list page)
 * - /document-templates (DocumentTemplate list page)
 * - /equity-grants (EquityGrant list page)
 * - /investment-terms (InvestmentTerm list page)
 * - /legal-addresses (LegalAddress list page)
 * - /legal-documents (LegalDocument list page)
 * - /legal-entities (LegalEntity list page)
 * - /template-clauses (TemplateClause list page)
 * - /vesting-schedules (VestingSchedule list page)
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
          path="contact-persons"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <ContactPersonPage />
            </Suspense>
          }
        />
        <Route
          path="document-parties"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <DocumentPartyPage />
            </Suspense>
          }
        />
        <Route
          path="document-templates"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <DocumentTemplatePage />
            </Suspense>
          }
        />
        <Route
          path="equity-grants"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <EquityGrantPage />
            </Suspense>
          }
        />
        <Route
          path="investment-terms"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <InvestmentTermPage />
            </Suspense>
          }
        />
        <Route
          path="legal-addresses"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <LegalAddressPage />
            </Suspense>
          }
        />
        <Route
          path="legal-documents"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <LegalDocumentPage />
            </Suspense>
          }
        />
        <Route
          path="legal-entities"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <LegalEntityPage />
            </Suspense>
          }
        />
        <Route
          path="template-clauses"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <TemplateClausePage />
            </Suspense>
          }
        />
        <Route
          path="vesting-schedules"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <VestingSchedulePage />
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
