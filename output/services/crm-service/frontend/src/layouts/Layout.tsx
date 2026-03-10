/**
 * Layout Component
 *
 * Main application layout with:
 * - Material-UI AppBar with navigation
 * - Responsive navigation drawer
 * - Active route highlighting
 * - Mobile-responsive collapsible drawer
 *
 * @description Application shell for crm
 * @generated 2026-03-10T13:09:26.115903Z
 */

import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Home as HomeIcon,
  ChevronLeft as ChevronLeftIcon,
  Logout as LogoutIcon,
  List as ListIcon,
} from '@mui/icons-material';
import { useAuth } from '../auth/AuthProvider';

// ============================================================================
// Constants
// ============================================================================

/** Width of the navigation drawer */
const DRAWER_WIDTH = 260;

/** Height of the app bar */
const APP_BAR_HEIGHT = 64;

// ============================================================================
// Types
// ============================================================================

/**
 * Navigation item definition
 */
interface NavItem {
  /** Route path */
  path: string;
  /** Display label */
  label: string;
  /** Icon component */
  icon: React.ReactElement;
}

// ============================================================================
// Navigation Configuration
// ============================================================================

/**
 * Navigation items for the sidebar
 *
 * Includes home link and links to all entity list pages.
 * Icons are mapped from entity configuration or use default ListIcon.
 */
const NAV_ITEMS: NavItem[] = [
  {
    path: '/',
    label: 'Home',
    icon: <HomeIcon />,
  },
  {
    path: '/activities',
    label: 'Activities',
    icon: <ListIcon />,
  },
  {
    path: '/pipeline-stages',
    label: 'Pipelinestages',
    icon: <ListIcon />,
  },
  {
    path: '/shortlists',
    label: 'Shortlists',
    icon: <ListIcon />,
  },
  {
    path: '/shortlist-tags',
    label: 'Shortlisttags',
    icon: <ListIcon />,
  },
  {
    path: '/tags',
    label: 'Tags',
    icon: <ListIcon />,
  },
];

// ============================================================================
// Component
// ============================================================================

/**
 * Layout Component
 *
 * Provides the main application shell with navigation drawer and app bar.
 * Renders child routes via React Router's Outlet component.
 */
export function Layout(): React.ReactElement {
  const theme = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  // Responsive breakpoint for mobile
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Mobile drawer state
  const [mobileOpen, setMobileOpen] = useState(false);

  const { user, logout } = useAuth();

  // User menu state
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const userMenuOpen = Boolean(userMenuAnchor);

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleLogout = async () => {
    handleUserMenuClose();
    await logout();
    navigate('/login');
  };

  /**
   * Toggle mobile drawer open/closed
   */
  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  /**
   * Navigate to a route and close mobile drawer if open
   */
  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  /**
   * Check if a navigation item is currently active
   */
  const isActive = (path: string): boolean => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  /**
   * Drawer content - navigation list
   */
  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Drawer Header */}
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: [1],
          minHeight: `${APP_BAR_HEIGHT}px !important`,
        }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            cursor: 'pointer',
          }}onClick={() => handleNavigation('/')}
        >
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 1,
              backgroundColor: '#1976d2',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
            <Typography variant="h6" sx={{ color: 'white', fontWeight: 700 }}>
              C
            </Typography>
          </Box>
          <Typography
            variant="h6"
            noWrap
            component="div"
            sx={{ fontWeight: 600 }}>
            crm
          </Typography>
        </Box>
        {isMobile && (
          <IconButton onClick={handleDrawerToggle}>
            <ChevronLeftIcon />
          </IconButton>
        )}
      </Toolbar>
      <Divider />

      {/* Navigation List */}
      <List sx={{ flex: 1, pt: 1 }}>
        {NAV_ITEMS.map((item) => (
          <ListItem key={item.path} disablePadding sx={{ px: 1 }}>
            <ListItemButton
              onClick={() => handleNavigation(item.path)}
              selected={isActive(item.path)}
              sx={{
                borderRadius: 1,
                mb: 0.5,
                '&.Mui-selected': {
                  backgroundColor: theme.palette.primary.main + '1A',
                  '&:hover': {
                    backgroundColor: theme.palette.primary.main + '26',
                  },
                  '& .MuiListItemIcon-root': {
                    color: theme.palette.primary.main,
                  },
                  '& .MuiListItemText-primary': {
                    color: theme.palette.primary.main,
                    fontWeight: 600,
                  },
                },
              }}>
              <ListItemIcon
                sx={{
                  minWidth: 40,
                  color: isActive(item.path)
                    ? theme.palette.primary.main
                    : theme.palette.text.secondary,
                }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: '0.875rem',
                  fontWeight: isActive(item.path) ? 600 : 400,
                }}/>
            </ListItemButton>
          </ListItem>
        ))}
      </List>

    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <CssBaseline />

      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: {md: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: {md: `${DRAWER_WIDTH}px` },
          backgroundColor: theme.palette.background.paper,
          color: theme.palette.text.primary,
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
        }}elevation={0}
      >
        <Toolbar sx={{ minHeight: `${APP_BAR_HEIGHT}px !important` }}>
          {/* Mobile Menu Button */}
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: {md: 'none' } }}>
            <MenuIcon />
          </IconButton>

          {/* Page Title - can be customized per route */}
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {/* Title is handled by individual pages */}
          </Typography>


          {/* User Menu */}
          <Tooltip title={user?.username ?? 'Account'}>
            <IconButton
              onClick={handleUserMenuOpen}
              size="small"
              aria-controls={userMenuOpen ? 'user-menu' : undefined}
              aria-haspopup="true"
              aria-expanded={userMenuOpen ? 'true' : undefined}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: '#1976d2' }}>
                {user?.username?.charAt(0).toUpperCase() ?? 'U'}
              </Avatar>
            </IconButton>
          </Tooltip>
          <Menu
            id="user-menu"
            anchorEl={userMenuAnchor}
            open={userMenuOpen}
            onClose={handleUserMenuClose}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}>
            <MenuItem onClick={handleLogout}>
              <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Navigation Drawer */}
      <Box
        component="nav"
        sx={{ width: {md: DRAWER_WIDTH }, flexShrink: {md: 0 } }}>
        {/* Mobile Drawer (Temporary) */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better mobile performance
          }}sx={{
            display: { xs: 'block',md: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}>
          {drawerContent}
        </Drawer>

        {/* Desktop Drawer (Permanent) */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none',md: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
              borderRight: '1px solid',
              borderColor: theme.palette.divider,
            },
          }}open
        >
          {drawerContent}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: {md: `calc(100% - ${DRAWER_WIDTH}px)` },
          minHeight: '100vh',
          backgroundColor: theme.palette.background.default,
          mt: `${APP_BAR_HEIGHT}px`,
        }}>
        {/* Outlet renders the child routes */}
        <Outlet />
      </Box>
    </Box>
  );
}

export default Layout;
