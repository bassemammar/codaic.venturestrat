/**
 * Material-UI Theme Configuration
 *
 * Centralized theme configuration for crm.
 * Provides consistent styling across all components with customizable
 * palette, typography, spacing, and component overrides.
 *
 * @description Theme configuration for Material-UI
 * @see https://mui.com/material-ui/customization/theming/
 * @generated 2026-03-10T13:09:26.115903Z
 */

import { createTheme, ThemeOptions, PaletteMode } from '@mui/material/styles';

// ============================================================================
// Color Palette
// ============================================================================

/**
 * Primary color palette
 *
 * @description Main brand colors used for primary actions and UI elements
 */
const primaryColors = {
  main: '#1976d2',
  contrastText: '#ffffff',
};

/**
 * Secondary color palette
 *
 * @description Accent colors used for secondary actions and highlights
 */
const secondaryColors = {
  main: '#dc004e',
  contrastText: '#ffffff',
};

/**
 * Semantic color palette
 *
 * @description Colors for status indicators and feedback
 */
const semanticColors = {
  error: {
    main: '#d32f2f',
  },
  warning: {
    main: '#ed6c02',
  },
  info: {
    main: '#0288d1',
  },
  success: {
    main: '#2e7d32',
  },
};

// ============================================================================
// Typography
// ============================================================================

/**
 * Typography configuration
 *
 * @description Font families, sizes, and weights for text elements
 * @see https://mui.com/material-ui/customization/typography/
 */
const typography = {
  fontFamily: [
    '-apple-system',
    'BlinkMacSystemFont',
    '"Segoe UI"',
    'Roboto',
    '"Helvetica Neue"',
    'Arial',
    'sans-serif',
    '"Apple Color Emoji"',
    '"Segoe UI Emoji"',
    '"Segoe UI Symbol"',
  ].join(','),
  fontSize: 14,
  htmlFontSize: 16,
  h1: {
    fontSize: '2.5rem',
    fontWeight: 500,
    lineHeight: 1.2,
    letterSpacing: '-0.01562em',
  },
  h2: {
    fontSize: '2rem',
    fontWeight: 500,
    lineHeight: 1.3,
    letterSpacing: '-0.00833em',
  },
  h3: {
    fontSize: '1.75rem',
    fontWeight: 500,
    lineHeight: 1.4,
    letterSpacing: '0em',
  },
  h4: {
    fontSize: '1.5rem',
    fontWeight: 500,
    lineHeight: 1.4,
    letterSpacing: '0.00735em',
  },
  h5: {
    fontSize: '1.25rem',
    fontWeight: 500,
    lineHeight: 1.5,
    letterSpacing: '0em',
  },
  h6: {
    fontSize: '1.125rem',
    fontWeight: 600,
    lineHeight: 1.5,
    letterSpacing: '0.0075em',
  },
  subtitle1: {
    fontSize: '1rem',
    fontWeight: 400,
    lineHeight: 1.75,
    letterSpacing: '0.00938em',
  },
  subtitle2: {
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: 1.57,
    letterSpacing: '0.00714em',
  },
  body1: {
    fontSize: '1rem',
    fontWeight: 400,
    lineHeight: 1.5,
    letterSpacing: '0.00938em',
  },
  body2: {
    fontSize: '0.875rem',
    fontWeight: 400,
    lineHeight: 1.43,
    letterSpacing: '0.01071em',
  },
  button: {
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: 1.75,
    letterSpacing: '0.02857em',
    textTransform: 'none' as const,
  },
  caption: {
    fontSize: '0.75rem',
    fontWeight: 400,
    lineHeight: 1.66,
    letterSpacing: '0.03333em',
  },
  overline: {
    fontSize: '0.75rem',
    fontWeight: 400,
    lineHeight: 2.66,
    letterSpacing: '0.08333em',
    textTransform: 'uppercase' as const,
  },
};

// ============================================================================
// Shape & Spacing
// ============================================================================

/**
 * Shape configuration
 *
 * @description Border radius and other shape properties
 */
const shape = {
  borderRadius: 8,
};

/**
 * Spacing configuration
 *
 * @description Base spacing unit (multiplied by theme.spacing() calls)
 * @example theme.spacing(2) = 16px
 */
const spacingUnit = 8;

// ============================================================================
// Component Overrides
// ============================================================================

/**
 * Component style overrides
 *
 * @description Customizes default component styles for consistent UI
 * @see https://mui.com/material-ui/customization/theme-components/
 */
const components: ThemeOptions['components'] = {
  MuiCssBaseline: {
    styleOverrides: {
      body: {
        scrollbarColor: '#c1c1c1 #f5f5f5',
        '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
          width: 8,
          height: 8,
        },
        '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
          borderRadius: 4,
          backgroundColor: '#c1c1c1',
          minHeight: 24,
        },
        '&::-webkit-scrollbar-thumb:hover, & *::-webkit-scrollbar-thumb:hover': {
          backgroundColor: '#a8a8a8',
        },
        '&::-webkit-scrollbar-track, & *::-webkit-scrollbar-track': {
          borderRadius: 4,
          backgroundColor: '#f5f5f5',
        },
      },
    },
  },
  MuiButton: {
    styleOverrides: {
      root: {
        textTransform: 'none',
        borderRadius: 8,
        fontWeight: 500,
      },
      contained: {
        boxShadow: 'none',
        '&:hover': {
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.15)',
        },
      },
      outlined: {
        borderWidth: 1,
        '&:hover': {
          borderWidth: 1,
        },
      },
    },
    defaultProps: {
      disableElevation: true,
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
      },
    },
    defaultProps: {
      elevation: 1,
    },
  },
  MuiCardHeader: {
    styleOverrides: {
      root: {
        padding: '16px 24px',
      },
      title: {
        fontSize: '1.125rem',
        fontWeight: 600,
      },
    },
  },
  MuiCardContent: {
    styleOverrides: {
      root: {
        padding: '16px 24px',
        '&:last-child': {
          paddingBottom: 24,
        },
      },
    },
  },
  MuiTextField: {
    defaultProps: {
      variant: 'outlined',
      size: 'medium',
    },
  },
  MuiOutlinedInput: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
          borderWidth: 2,
        },
      },
    },
  },
  MuiFilledInput: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        borderBottomLeftRadius: 0,
        borderBottomRightRadius: 0,
      },
    },
  },
  MuiInputLabel: {
    styleOverrides: {
      root: {
        fontSize: '0.875rem',
      },
    },
  },
  MuiSelect: {
    defaultProps: {
      variant: 'outlined',
      size: 'medium',
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        borderRadius: 6,
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        backgroundImage: 'none',
      },
      rounded: {
        borderRadius: 8,
      },
      elevation1: {
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
      },
      elevation2: {
        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.1)',
      },
      elevation3: {
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.12)',
      },
    },
  },
  MuiDialog: {
    styleOverrides: {
      paper: {
        borderRadius: 12,
      },
    },
  },
  MuiDialogTitle: {
    styleOverrides: {
      root: {
        padding: '16px 24px',
        fontWeight: 600,
      },
    },
  },
  MuiDialogContent: {
    styleOverrides: {
      root: {
        padding: '16px 24px',
      },
    },
  },
  MuiDialogActions: {
    styleOverrides: {
      root: {
        padding: '12px 24px',
      },
    },
  },
  MuiTableHead: {
    styleOverrides: {
      root: {
        '& .MuiTableCell-head': {
          fontWeight: 600,
          fontSize: '0.875rem',
        },
      },
    },
  },
  MuiTableBody: {
    styleOverrides: {
      root: {
        '& .MuiTableRow-root:hover': {
          backgroundColor: 'rgba(0, 0, 0, 0.04)',
        },
      },
    },
  },
  MuiTableCell: {
    styleOverrides: {
      root: {
      },
    },
  },
  MuiTablePagination: {
    styleOverrides: {
      root: {
        borderTop: '1px solid',
        borderColor: 'divider',
      },
    },
  },
  MuiTab: {
    styleOverrides: {
      root: {
        textTransform: 'none',
        fontWeight: 500,
        minWidth: 'auto',
      },
    },
  },
  MuiTabs: {
    styleOverrides: {
      indicator: {
        height: 3,
        borderTopLeftRadius: 3,
        borderTopRightRadius: 3,
      },
    },
  },
  MuiAlert: {
    styleOverrides: {
      root: {
        borderRadius: 8,
      },
      standardSuccess: {
        backgroundColor: 'rgba(46, 125, 50, 0.1)',
      },
      standardError: {
        backgroundColor: 'rgba(211, 47, 47, 0.1)',
      },
      standardWarning: {
        backgroundColor: 'rgba(237, 108, 2, 0.1)',
      },
      standardInfo: {
        backgroundColor: 'rgba(2, 136, 209, 0.1)',
      },
    },
  },
  MuiTooltip: {
    styleOverrides: {
      tooltip: {
        borderRadius: 4,
        fontSize: '0.75rem',
      },
    },
  },
  MuiDrawer: {
    styleOverrides: {
      paper: {
        borderRight: '1px solid',
        borderColor: 'divider',
      },
    },
  },
  MuiAppBar: {
    styleOverrides: {
      root: {
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
      },
    },
    defaultProps: {
      elevation: 0,
    },
  },
  MuiLinearProgress: {
    styleOverrides: {
      root: {
        borderRadius: 4,
        height: 6,
      },
    },
  },
  MuiCircularProgress: {
    styleOverrides: {
      root: {
        // Default styles
      },
    },
  },
  MuiSkeleton: {
    styleOverrides: {
      root: {
        borderRadius: 4.0,
      },
    },
  },
  MuiAvatar: {
    styleOverrides: {
      root: {
      },
    },
  },
  MuiBreadcrumbs: {
    styleOverrides: {
      root: {
        fontSize: '0.875rem',
      },
    },
  },
  MuiListItemButton: {
    styleOverrides: {
      root: {
        borderRadius: 4.0,
      },
    },
  },
  MuiListItemIcon: {
    styleOverrides: {
      root: {
        minWidth: 40,
      },
    },
  },
  MuiMenu: {
    styleOverrides: {
      paper: {
        borderRadius: 8,
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.12)',
      },
    },
  },
  MuiMenuItem: {
    styleOverrides: {
      root: {
      },
    },
  },
  MuiSnackbar: {
    styleOverrides: {
      root: {
        '& .MuiPaper-root': {
          borderRadius: 8,
        },
      },
    },
  },
};

// ============================================================================
// Theme Factory Functions
// ============================================================================

/**
 * Get design tokens based on palette mode
 *
 * @description Returns palette configuration for light or dark mode
 * @param mode - 'light' or 'dark' palette mode
 * @returns ThemeOptions object with mode-specific palette
 */
export const getDesignTokens = (mode: PaletteMode): ThemeOptions => ({
  palette: {
    mode,
    primary: primaryColors,
    secondary: secondaryColors,
    ...semanticColors,
    background: {
      default: mode === 'dark'
        ? '#121212'
        : '#f5f5f5',
      paper: mode === 'dark'
        ? '#1e1e1e'
        : '#ffffff',
    },
    text: {
      primary: mode === 'dark' ? '#ffffff' : 'rgba(0, 0, 0, 0.87)',
      secondary: mode === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.6)',
      disabled: mode === 'dark' ? 'rgba(255, 255, 255, 0.5)' : 'rgba(0, 0, 0, 0.38)',
    },
    divider: mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)',
    action: {
      active: mode === 'dark' ? 'rgba(255, 255, 255, 0.56)' : 'rgba(0, 0, 0, 0.54)',
      hover: mode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)',
      selected: mode === 'dark' ? 'rgba(255, 255, 255, 0.16)' : 'rgba(0, 0, 0, 0.08)',
      disabled: mode === 'dark' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.26)',
      disabledBackground: mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)',
    },
  },
  typography,
  shape,
  spacing: spacingUnit,
  components: {
    ...components,
    // Mode-specific component overrides
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 600,
            fontSize: '0.875rem',
            backgroundColor: mode === 'dark' ? '#2d2d2d' : '#f5f5f5',
          },
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarColor: mode === 'dark' ? '#555555 #2d2d2d' : '#c1c1c1 #f5f5f5',
          '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
            width: 8,
            height: 8,
          },
          '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
            borderRadius: 4,
            backgroundColor: mode === 'dark' ? '#555555' : '#c1c1c1',
            minHeight: 24,
          },
          '&::-webkit-scrollbar-thumb:hover, & *::-webkit-scrollbar-thumb:hover': {
            backgroundColor: mode === 'dark' ? '#6b6b6b' : '#a8a8a8',
          },
          '&::-webkit-scrollbar-track, & *::-webkit-scrollbar-track': {
            borderRadius: 4,
            backgroundColor: mode === 'dark' ? '#2d2d2d' : '#f5f5f5',
          },
        },
      },
    },
    MuiTableBody: {
      styleOverrides: {
        root: {
          '& .MuiTableRow-root:hover': {
            backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)',
          },
        },
      },
    },
  },
  colorSchemes: {
    light: true,
    dark: true,
  },
});

// ============================================================================
// Theme Export
// ============================================================================

/**
 * Default theme instance
 *
 * @description Pre-configured theme for light mode
 * @see https://mui.com/material-ui/customization/theming/#createtheme-options-args-theme
 */
export const theme = createTheme(getDesignTokens('light'));

/**
 * Light theme instance
 *
 * @description Pre-configured theme for light mode
 */
export const lightTheme = createTheme(getDesignTokens('light'));

/**
 * Dark theme instance
 *
 * @description Pre-configured theme for dark mode
 */
export const darkTheme = createTheme(getDesignTokens('dark'));


export default theme;
