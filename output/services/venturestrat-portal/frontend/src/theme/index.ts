import { createTheme } from '@mui/material/styles';

export const venturestratTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#4f7df9' },
    secondary: { main: '#ab47bc' },
    background: { default: '#f9fafb', paper: '#ffffff' },
    text: { primary: '#1a1a1a', secondary: '#6b7280' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
});

export { MODULE_CONFIGS, MODULE_LIST } from './moduleColors';
export type { ModuleId, ModuleConfig } from './moduleColors';
