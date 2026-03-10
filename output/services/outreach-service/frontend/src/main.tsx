import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './App';
import './index.css';

/**
 * QueryClient Configuration
 *
 * @description Centralized configuration for React Query data fetching.
 * @see https://tanstack.com/query/latest/docs/reference/QueryClient
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Time in ms before data is considered stale and may be refetched
      staleTime: 300000,
      // Time in ms before inactive queries are garbage collected
      gcTime: 300000,
      // Number of retry attempts for failed queries
      retry: 1,
      // Whether to refetch queries when window regains focus
      refetchOnWindowFocus: false,
      // Whether to refetch queries on network reconnect
      refetchOnReconnect: true,
      // Whether to refetch queries when component mounts
      refetchOnMount: true,
    },
    mutations: {
      // Number of retry attempts for failed mutations
      retry: 0,
    },
  },
});

/**
 * Application Entry Point
 *
 * Renders the React application with the following provider hierarchy:
 * - React.StrictMode: Development mode checks for potential problems
 * - QueryClientProvider: React Query context for data fetching
 * - BrowserRouter: React Router context for navigation
 * - App: The root application component
 *
 * @see https://react.dev/reference/react-dom/client/createRoot
 */
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
      <ReactQueryDevtools
        initialIsOpen={false}
        buttonPosition="bottom-right"
      />
    </QueryClientProvider>
  </React.StrictMode>,
);
