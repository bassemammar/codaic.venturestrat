/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const serviceRoutes: Record<string, { target: string; rewrite?: (path: string) => string }> = {
  // Auth service (8106)
  '/api/v1/auth': { target: 'http://127.0.0.1:8106' },

  // Event monitor (8101)
  '/api/v1/events': { target: 'http://127.0.0.1:8101' },

  // Forge (8150)
  '/api/v1/forge': { target: 'http://127.0.0.1:8150' },

  // investor-service (8060)
  '/api/v1/investors': { target: 'http://127.0.0.1:8059' },
  '/api/v1/investor-emails': { target: 'http://127.0.0.1:8059' },
  '/api/v1/investor-markets': { target: 'http://127.0.0.1:8059' },
  '/api/v1/investor-past-investments': { target: 'http://127.0.0.1:8059' },
  '/api/v1/markets': { target: 'http://127.0.0.1:8059' },
  '/api/v1/past-investments': { target: 'http://127.0.0.1:8059' },

  // outreach-service (8061)
  '/api/v1/ai': { target: 'http://127.0.0.1:8061' },
  '/api/v1/attachments': { target: 'http://127.0.0.1:8061' },
  '/api/v1/email-accounts': { target: 'http://127.0.0.1:8061' },
  '/api/v1/email-templates': { target: 'http://127.0.0.1:8061' },
  '/api/v1/lifecycle-emails': { target: 'http://127.0.0.1:8061' },
  '/api/v1/messages': { target: 'http://127.0.0.1:8061' },
  '/api/v1/oauth': { target: 'http://127.0.0.1:8061' },

  // crm-service (8062)
  '/api/v1/activities': { target: 'http://127.0.0.1:8062' },
  '/api/v1/pipeline-stages': { target: 'http://127.0.0.1:8062' },
  '/api/v1/shortlists': { target: 'http://127.0.0.1:8062' },
  '/api/v1/shortlist-tags': { target: 'http://127.0.0.1:8062' },
  '/api/v1/tags': { target: 'http://127.0.0.1:8062' },

  // billing-service (8063)
  '/api/v1/plans': { target: 'http://127.0.0.1:8063' },
  '/api/v1/subscriptions': { target: 'http://127.0.0.1:8063' },
  '/api/v1/usage-records': { target: 'http://127.0.0.1:8063' },

  // legal-service (8064)
  '/api/v1/documents': { target: 'http://127.0.0.1:8064' },
  '/api/v1/legal-documents': { target: 'http://127.0.0.1:8064' },
  '/api/v1/document-parties': { target: 'http://127.0.0.1:8064' },
  '/api/v1/legal-entities': { target: 'http://127.0.0.1:8064' },
  '/api/v1/contact-persons': { target: 'http://127.0.0.1:8064' },
  '/api/v1/legal-addresses': { target: 'http://127.0.0.1:8064' },
  '/api/v1/document-templates': { target: 'http://127.0.0.1:8064' },
  '/api/v1/template-clauses': { target: 'http://127.0.0.1:8064' },
  '/api/v1/equity-grants': { target: 'http://127.0.0.1:8064' },
  '/api/v1/vesting-schedules': { target: 'http://127.0.0.1:8064' },
  '/api/v1/investment-terms': { target: 'http://127.0.0.1:8064' },
};

function buildProxyConfig() {
  const proxy: Record<string, object> = {};
  for (const [apiPath, config] of Object.entries(serviceRoutes)) {
    const entry: Record<string, unknown> = {
      target: config.target,
      changeOrigin: true,
      secure: false,
    };
    if (config.rewrite) {
      entry.rewrite = config.rewrite;
    }
    proxy[apiPath] = entry;
  }
  return proxy;
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@modules': path.resolve(__dirname, './src/modules'),
      '@shared': path.resolve(__dirname, './src/shared'),
      '@layouts': path.resolve(__dirname, './src/layouts'),
      '@theme': path.resolve(__dirname, './src/theme'),
      '@inve': path.resolve(__dirname, '../../investor-service/frontend/src'),
      '@outr': path.resolve(__dirname, '../../outreach-service/frontend/src'),
      '@crm': path.resolve(__dirname, '../../crm-service/frontend/src'),
      '@bill': path.resolve(__dirname, '../../billing-service/frontend/src'),
      '@legal': path.resolve(__dirname, '../../legal-service/frontend/src'),
    },
    dedupe: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query', '@mui/material', '@mui/system', '@emotion/react', '@emotion/styled'],
  },
  server: {
    port: 5177,
    host: true,
    proxy: buildProxyConfig(),
    fs: {
      allow: [
        path.resolve(__dirname, '.'),
        path.resolve(__dirname, '../../investor-service/frontend'),
        path.resolve(__dirname, '../../outreach-service/frontend'),
        path.resolve(__dirname, '../../crm-service/frontend'),
        path.resolve(__dirname, '../../billing-service/frontend'),
        path.resolve(__dirname, '../../legal-service/frontend'),
        path.resolve(__dirname, '../../../node_modules'),
      ],
    },
  },
  preview: { port: 6177, host: true },
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2020',
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'query-vendor': ['@tanstack/react-query'],
          'mui-vendor': ['@mui/material', '@mui/icons-material'],
          'chart-vendor': ['recharts', 'react-grid-layout'],
          'geo-data': ['country-state-city'],
        },
      },
    },
  },
  test: { globals: true, environment: 'jsdom', css: true, setupFiles: ['./src/setupTests.ts'], include: ['src/**/*.{test,spec}.{ts,tsx}'], exclude: ['node_modules/**', 'dist/**'] },
  define: { __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.1.0') },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query', '@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled', 'axios', 'recharts', 'lucide-react'],
  },
});
