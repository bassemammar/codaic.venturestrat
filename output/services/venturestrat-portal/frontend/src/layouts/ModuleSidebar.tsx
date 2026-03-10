import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  Collapse,
} from '@mui/material';
import {
  Home,
  Scale,
  TrendingUp,
  Mail,
  HelpCircle,
  CreditCard,
  Settings,
  LogOut,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { useSubscriptionStatus } from '../modules/investor/hooks/useSubscriptionStatus';

const ACCENT = '#4f7df9';

interface NavItem {
  label: string;
  icon: React.ReactElement;
  path?: string;
  action?: () => void;
  children?: { label: string; path: string }[];
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const SidebarNavItem: React.FC<{
  item: NavItem;
  isActive: (p: string) => boolean;
  navigate: (p: string) => void;
}> = ({ item, isActive, navigate }) => {
  const [open, setOpen] = React.useState(() => {
    if (!item.children) return false;
    // Auto-expand if any child is active
    const loc = window.location.pathname;
    return item.children.some((c) => loc === c.path || loc.startsWith(c.path + '/'));
  });

  // Simple nav item (no children)
  if (!item.children) {
    const active = item.path ? isActive(item.path) : false;
    return (
      <ListItem disablePadding sx={{ px: 1 }}>
        <ListItemButton
          onClick={() => {
            if (item.action) item.action();
            else if (item.path) navigate(item.path);
          }}
          selected={active}
          sx={{
            borderRadius: 1,
            mb: 0.25,
            py: 0.75,
            '&.Mui-selected': {
              bgcolor: `${ACCENT}14`,
              '&:hover': { bgcolor: `${ACCENT}20` },
              '& .MuiListItemIcon-root': { color: ACCENT },
              '& .MuiListItemText-primary': { color: ACCENT, fontWeight: 600 },
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: 32, color: active ? ACCENT : '#6b7280' }}>
            {item.icon}
          </ListItemIcon>
          <ListItemText
            primary={item.label}
            primaryTypographyProps={{
              fontSize: '0.85rem',
              fontWeight: active ? 600 : 400,
              color: active ? ACCENT : '#374151',
            }}
          />
        </ListItemButton>
      </ListItem>
    );
  }

  // Expandable nav item
  const anyChildActive = item.children.some((c) => isActive(c.path));

  return (
    <>
      <ListItem disablePadding sx={{ px: 1 }}>
        <ListItemButton
          onClick={() => setOpen((prev) => !prev)}
          sx={{
            borderRadius: 1,
            mb: 0.25,
            py: 0.75,
            ...(anyChildActive && {
              '& .MuiListItemIcon-root': { color: ACCENT },
              '& .MuiListItemText-primary': { color: ACCENT, fontWeight: 600 },
            }),
          }}
        >
          <ListItemIcon sx={{ minWidth: 32, color: anyChildActive ? ACCENT : '#6b7280' }}>
            {item.icon}
          </ListItemIcon>
          <ListItemText
            primary={item.label}
            primaryTypographyProps={{
              fontSize: '0.85rem',
              fontWeight: anyChildActive ? 600 : 400,
              color: anyChildActive ? ACCENT : '#374151',
            }}
          />
          {open
            ? <ChevronDown size={14} color="#9ca3af" />
            : <ChevronRight size={14} color="#9ca3af" />
          }
        </ListItemButton>
      </ListItem>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <List disablePadding>
          {item.children.map((child) => {
            const active = isActive(child.path);
            return (
              <ListItem key={child.path} disablePadding sx={{ px: 1 }}>
                <ListItemButton
                  onClick={() => navigate(child.path)}
                  selected={active}
                  sx={{
                    borderRadius: 1,
                    mb: 0.25,
                    py: 0.5,
                    pl: 5.5,
                    '&.Mui-selected': {
                      bgcolor: `${ACCENT}14`,
                      '&:hover': { bgcolor: `${ACCENT}20` },
                      '& .MuiListItemText-primary': { color: ACCENT, fontWeight: 600 },
                    },
                  }}
                >
                  <ListItemText
                    primary={child.label}
                    primaryTypographyProps={{
                      fontSize: '0.82rem',
                      fontWeight: active ? 600 : 400,
                      color: active ? ACCENT : '#6b7280',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Collapse>
    </>
  );
};

const ModuleSidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { data: subStatus } = useSubscriptionStatus();

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const sections: NavSection[] = [
    {
      title: 'Main Menu',
      items: [
        { label: 'Home', icon: <Home size={18} />, path: '/' },
        {
          label: 'Legal',
          icon: <Scale size={18} />,
          children: [
            { label: 'Overview', path: '/legal' },
            { label: 'Document Wizard', path: '/legal/wizard' },
            { label: 'Terms & Privacy', path: '/legal/terms' },
          ],
        },
        {
          label: 'Fundraising',
          icon: <TrendingUp size={18} />,
          children: [
            { label: 'Investors', path: '/investor/search' },
            { label: 'CRM', path: '/crm/kanban' },
          ],
        },
        { label: 'Mail', icon: <Mail size={18} />, path: '/outreach/mail' },
      ],
    },
    {
      title: 'Other',
      items: [
        { label: 'Help Center', icon: <HelpCircle size={18} />, path: '/help' },
        { label: 'Subscriptions', icon: <CreditCard size={18} />, path: '/billing/subscription' },
        { label: 'Settings', icon: <Settings size={18} />, path: '/settings' },
        { label: 'Log Out', icon: <LogOut size={18} />, action: handleLogout },
      ],
    },
  ];

  return (
    <Box sx={{ width: '100%', py: 1.5 }}>
      {/* User account card */}
      {user && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            px: 2,
            py: 1.5,
            mx: 1,
            mb: 1,
            borderRadius: 1.5,
            bgcolor: '#f3f4f6',
          }}
        >
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 1,
              bgcolor: '#e5e7eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Typography sx={{ fontSize: 14, fontWeight: 700, color: '#6b7280' }}>
              {user.username?.charAt(0).toUpperCase() ?? 'U'}
            </Typography>
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography
              sx={{
                fontSize: 13,
                fontWeight: 600,
                color: '#1a1a1a',
                lineHeight: 1.3,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {user.username ?? 'User'}
            </Typography>
            <Typography sx={{ fontSize: 11, color: '#9ca3af', lineHeight: 1.3 }}>
              {subStatus?.planName ?? 'Free'}
            </Typography>
          </Box>
        </Box>
      )}
      {sections.map((section, idx) => (
        <Box key={section.title}>
          {idx > 0 && <Divider sx={{ borderColor: '#e5e7eb', my: 1 }} />}
          <Box sx={{ px: 2, py: 0.75 }}>
            <Typography
              variant="overline"
              sx={{
                color: '#9ca3af',
                fontWeight: 700,
                fontSize: '0.68rem',
                letterSpacing: '0.08em',
              }}
            >
              {section.title}
            </Typography>
          </Box>
          <List disablePadding>
            {section.items.map((item) => (
              <SidebarNavItem
                key={item.label}
                item={item}
                isActive={isActive}
                navigate={navigate}
              />
            ))}
          </List>
        </Box>
      ))}
    </Box>
  );
};

export default ModuleSidebar;
