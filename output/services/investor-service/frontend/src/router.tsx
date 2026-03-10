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
const InvestorPage = lazy(() => import('./pages/InvestorPage'));
const InvestorEmailPage = lazy(() => import('./pages/InvestorEmailPage'));
const InvestorMarketPage = lazy(() => import('./pages/InvestorMarketPage'));
const InvestorPastInvestmentPage = lazy(() => import('./pages/InvestorPastInvestmentPage'));
const MarketPage = lazy(() => import('./pages/MarketPage'));
const PastInvestmentPage = lazy(() => import('./pages/PastInvestmentPage'));
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
 * - /investors (Investor list page)
 * - /investor-emails (InvestorEmail list page)
 * - /investor-markets (InvestorMarket list page)
 * - /investor-past-investments (InvestorPastInvestment list page)
 * - /markets (Market list page)
 * - /past-investments (PastInvestment list page)
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
          path="investors"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <InvestorPage />
            </Suspense>
          }
        />
        <Route
          path="investor-emails"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <InvestorEmailPage />
            </Suspense>
          }
        />
        <Route
          path="investor-markets"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <InvestorMarketPage />
            </Suspense>
          }
        />
        <Route
          path="investor-past-investments"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <InvestorPastInvestmentPage />
            </Suspense>
          }
        />
        <Route
          path="markets"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <MarketPage />
            </Suspense>
          }
        />
        <Route
          path="past-investments"
          element={
            <Suspense fallback={<PageLoadingFallback />}>
              <PastInvestmentPage />
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
