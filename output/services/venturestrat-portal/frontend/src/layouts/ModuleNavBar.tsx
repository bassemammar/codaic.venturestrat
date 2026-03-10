import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Box, Tooltip, IconButton, Typography } from '@mui/material';
import { Home, LayoutDashboard, Radio, Anvil, Box as BoxIcon, UserCheck } from 'lucide-react';
import { MODULE_LIST, type ModuleId } from '../theme/moduleColors';

const ICON_MAP: Record<string, React.ReactElement> = {
  Box: <BoxIcon size={16} />,
  UserCheck: <UserCheck size={16} />,
};

interface ModuleNavBarProps {
  activeModule: ModuleId | null;
}

const ModuleNavBar: React.FC<ModuleNavBarProps> = ({ activeModule }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isHome = location.pathname === '/';
  const isDashboard = location.pathname.startsWith('/dashboard');

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, px: 1, py: 0.5, borderBottom: '1px solid', borderColor: '#e5e7eb', bgcolor: '#ffffff', overflowX: 'auto', minHeight: 48 }}>
      <Tooltip title="Home">
        <IconButton size="small" onClick={() => navigate('/')} sx={{ borderRadius: 1, bgcolor: isHome ? '#eff6ff' : 'transparent', color: isHome ? '#4f7df9' : '#6b7280', '&:hover': { bgcolor: isHome ? '#dbeafe' : '#f3f4f6' } }}>
          <Home size={16} />
        </IconButton>
      </Tooltip>
      <Tooltip title="Dashboard">
        <IconButton size="small" onClick={() => navigate('/dashboard')} sx={{ borderRadius: 1, bgcolor: isDashboard ? '#eff6ff' : 'transparent', color: isDashboard ? '#4f7df9' : '#6b7280', '&:hover': { bgcolor: isDashboard ? '#dbeafe' : '#f3f4f6' } }}>
          <LayoutDashboard size={16} />
        </IconButton>
      </Tooltip>
      <Tooltip title="Event Monitor">
        <IconButton size="small" onClick={() => navigate('/events')} sx={{ borderRadius: 1, bgcolor: location.pathname.startsWith('/events') ? '#fff7ed' : 'transparent', color: location.pathname.startsWith('/events') ? '#ea580c' : '#6b7280', '&:hover': { bgcolor: location.pathname.startsWith('/events') ? '#ffedd5' : '#f3f4f6' } }}>
          <Radio size={16} />
        </IconButton>
      </Tooltip>
      <Tooltip title="Forge Admin">
        <IconButton size="small" onClick={() => navigate('/forge/admin')} sx={{ borderRadius: 1, bgcolor: location.pathname.startsWith('/forge') ? '#fff7ed' : 'transparent', color: location.pathname.startsWith('/forge') ? '#d97706' : '#6b7280', '&:hover': { bgcolor: location.pathname.startsWith('/forge') ? '#fef3c7' : '#f3f4f6' } }}>
          <Anvil size={16} />
        </IconButton>
      </Tooltip>
      <Box sx={{ width: 1, height: 24, bgcolor: '#e5e7eb', mx: 0.5 }} />
      {MODULE_LIST.map((mod) => {
        const isActive = activeModule === mod.id;
        return (
          <Tooltip key={mod.id} title={mod.label}>
            <Box onClick={() => navigate(`/${mod.id}`)} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, px: 1.5, py: 0.5, borderRadius: 1, cursor: 'pointer', bgcolor: isActive ? `${mod.accent}14` : 'transparent', border: isActive ? `1px solid ${mod.accent}40` : '1px solid transparent', color: isActive ? mod.accent : '#6b7280', '&:hover': { bgcolor: `${mod.accent}0A`, color: mod.accent }, transition: 'all 0.15s', whiteSpace: 'nowrap' }}>
              {ICON_MAP[mod.icon] || <Home size={16} />}
              <Typography variant="caption" fontWeight={isActive ? 600 : 400} sx={{ fontSize: '0.75rem' }}>{mod.label}</Typography>
            </Box>
          </Tooltip>
        );
      })}
    </Box>
  );
};

export default ModuleNavBar;
