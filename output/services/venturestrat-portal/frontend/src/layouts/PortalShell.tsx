import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AppBar, Avatar, Box, Drawer, IconButton, Menu, MenuItem, ListItemIcon, Toolbar, Tooltip, Typography, useTheme, useMediaQuery } from '@mui/material';
import { Menu as MenuIcon, LogOut as LogOutIcon, Settings as SettingsIcon, PanelLeftClose } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import ModuleSidebar from './ModuleSidebar';
import TrialBanner from '../modules/billing/components/TrialBanner';
import { useSubscriptionStatus } from '../modules/investor/hooks/useSubscriptionStatus';

const DRAWER_WIDTH = 260;
const APPBAR_HEIGHT = 48;
const TRIAL_BANNER_HEIGHT = 36;
const SESSION_DISMISS_KEY = 'trial_banner_dismissed';

const PortalShell: React.FC = () => {
  const theme = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);

  // Track banner dismiss so layout offsets stay in sync
  const [bannerDismissed, setBannerDismissed] = useState<boolean>(
    () => sessionStorage.getItem(SESSION_DISMISS_KEY) === '1',
  );
  const { data: subStatus } = useSubscriptionStatus();
  const showBanner = !!user && !!subStatus?.isTrialing && !bannerDismissed;
  const bannerHeight = showBanner ? TRIAL_BANNER_HEIGHT : 0;
  const totalHeaderHeight = APPBAR_HEIGHT + bannerHeight;

  const handleLogout = async () => {
    setUserMenuAnchor(null);
    await logout();
    navigate('/login');
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          bgcolor: '#ffffff',
          color: 'text.primary',
          borderBottom: '1px solid',
          borderColor: '#e5e7eb',
          zIndex: theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar sx={{ minHeight: `${APPBAR_HEIGHT}px !important`, px: 2 }}>
          {isMobile && (
            <IconButton
              edge="start"
              onClick={() => setMobileOpen(!mobileOpen)}
              sx={{ mr: 1, color: '#6b7280' }}
            >
              <MenuIcon size={18} />
            </IconButton>
          )}
          <Box
            sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }}
            onClick={() => navigate('/')}
          >
            <Box
              sx={{
                width: 28,
                height: 28,
                borderRadius: 0.5,
                bgcolor: '#4f7df9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography
                sx={{
                  color: '#ffffff',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  fontFamily: '"JetBrains Mono", monospace',
                }}
              >
                V
              </Typography>
            </Box>
            <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#1a1a1a' }}>
              <Box component="span" sx={{ color: '#1a1a1a' }}>VENTURE</Box>
              <Box component="span" sx={{ color: '#4f7df9' }}>STRAT</Box>
            </Typography>
          </Box>
          {!isMobile && (
            <Tooltip title="Toggle sidebar">
              <IconButton
                size="small"
                onClick={() => setSidebarCollapsed((prev) => !prev)}
                sx={{ ml: 0.5, color: '#9ca3af', '&:hover': { color: '#6b7280' } }}
              >
                <PanelLeftClose size={16} />
              </IconButton>
            </Tooltip>
          )}
          <Box sx={{ flexGrow: 1 }} />
          {user && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mr: 1.5 }}>
              <Box sx={{ textAlign: 'right' }}>
                <Typography sx={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', lineHeight: 1.2 }}>
                  {user.username ?? 'User'}
                </Typography>
                <Typography sx={{ fontSize: 11, color: '#9ca3af', lineHeight: 1.2 }}>
                  {subStatus?.planName ?? 'Free'}
                </Typography>
              </Box>
            </Box>
          )}
          <Tooltip title={user?.username ?? 'Account'}>
            <IconButton onClick={(e) => setUserMenuAnchor(e.currentTarget)} size="small">
              <Avatar
                sx={{
                  width: 30,
                  height: 30,
                  bgcolor: '#4f7df9',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                }}
              >
                {user?.username?.charAt(0).toUpperCase() ?? 'U'}
              </Avatar>
            </IconButton>
          </Tooltip>
          <Menu
            anchorEl={userMenuAnchor}
            open={!!userMenuAnchor}
            onClose={() => setUserMenuAnchor(null)}
          >
            <MenuItem
              onClick={() => {
                setUserMenuAnchor(null);
                navigate('/settings');
              }}
            >
              <ListItemIcon><SettingsIcon size={16} /></ListItemIcon>
              Settings
            </MenuItem>
            <MenuItem onClick={handleLogout}>
              <ListItemIcon><LogOutIcon size={16} /></ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Fixed strip: trial banner */}
      {user && (
        <Box
          sx={{
            mt: `${APPBAR_HEIGHT}px`,
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            zIndex: theme.zIndex.drawer,
          }}
        >
          <TrialBanner onDismiss={() => setBannerDismissed(true)} />
        </Box>
      )}

      {/* Content area pushed below fixed header */}
      <Box
        sx={{
          display: 'flex',
          mt: `${totalHeaderHeight}px`,
          minHeight: `calc(100vh - ${totalHeaderHeight}px)`,
        }}
      >
        {/* Sidebar always visible */}
        {isMobile ? (
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={() => setMobileOpen(false)}
            ModalProps={{ keepMounted: true }}
            sx={{
              '& .MuiDrawer-paper': {
                width: DRAWER_WIDTH,
                mt: `${totalHeaderHeight}px`,
                bgcolor: '#ffffff',
                borderRight: '1px solid #e5e7eb',
              },
            }}
          >
            <ModuleSidebar />
          </Drawer>
        ) : !sidebarCollapsed ? (
          <Box
            sx={{
              width: DRAWER_WIDTH,
              flexShrink: 0,
              borderRight: '1px solid',
              borderColor: '#e5e7eb',
              bgcolor: '#ffffff',
              overflowY: 'auto',
              height: `calc(100vh - ${totalHeaderHeight}px)`,
              position: 'sticky',
              top: `${totalHeaderHeight}px`,
            }}
          >
            <ModuleSidebar />
          </Box>
        ) : null}
        <Box
          component="main"
          sx={{ flexGrow: 1, p: 3, bgcolor: '#f9fafb', minHeight: '100%', overflow: 'auto' }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default PortalShell;
