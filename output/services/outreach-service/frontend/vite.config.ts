/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

/**
 * Vite Configuration
 *
 * @description Build and development configuration for outreach
 * @see https://vite.dev/config/
 * @generated 2026-03-10T13:09:41.930152Z
 */
export default defineConfig({
  plugins: [
    react(),
  ],

  resolve: {
    alias: {
      // Standard path aliases for clean imports
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@layouts': path.resolve(__dirname, './src/layouts'),
      '@services': path.resolve(__dirname, './src/services'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@types': path.resolve(__dirname, './src/types'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
    // Dedupe packages to prevent multiple React instances and context issues
    dedupe: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      '@mui/material',
      '@mui/system',
      '@emotion/react',
      '@emotion/styled',
    ],
  },

  server: {
    port: 5173,
    host: true,
    open: true,
    proxy: {
      // Auth service proxy (must be before catch-all)
      '/api/v1/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy API calls to backend service
      '/api': {
        target: 'http://localhost:8061',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  preview: {
    port: 4173,
    host: true,
  },

  build: {
    outDir: 'dist',
    sourcemap: true,
    // Target modern browsers for smaller bundles
    target: 'es2020',
    // Chunk size warning threshold (in kB)
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Manual chunks for optimal caching
        manualChunks: {
          // React core libraries - rarely change
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // Data fetching - changes independently
          'query-vendor': ['@tanstack/react-query'],
          // UI library - large but stable
          'mui-vendor': ['@mui/material', '@mui/icons-material'],
        },
      },
    },
  },

  // Vitest configuration (when running `npm run test`)
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      'node_modules/**',
      'dist/**',
      'tests/**',
      '**/*.e2e.{test,spec}.{ts,tsx}',
      '**/e2e/**',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData/**',
        '**/__mocks__/**',
        '**/*.stories.tsx',
        'src/main.tsx',
        'src/vite-env.d.ts',
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },

  // Define environment variables that can be accessed at runtime
  // These must be prefixed with VITE_ to be exposed to the client
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.1.0'),
  },

  // Optimize dependencies for faster dev server startup
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      '@mui/material',
      '@mui/icons-material',
      '@emotion/react',
      '@emotion/styled',
      'axios',
    ],
  },
});
