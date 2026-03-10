import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, List, ListItem, ListItemButton, ListItemText } from '@mui/material';
import { MODULE_CONFIGS, type ModuleId } from '../theme/moduleColors';

interface ModuleHomeProps { moduleId: string; }

const ModuleHome: React.FC<ModuleHomeProps> = ({ moduleId }) => {
  const navigate = useNavigate();
  const config = MODULE_CONFIGS[moduleId as ModuleId];
  if (!config) return <Typography>Module not found</Typography>;

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', py: 4 }}>
      <Typography variant="h5" fontWeight={700} sx={{ color: config.accent, mb: 0.5 }}>{config.label}</Typography>
      <Typography variant="body1" sx={{ color: '#6b7280', mb: 3 }}>{config.description}</Typography>
      <Typography variant="subtitle2" sx={{ color: '#6b7280', mb: 1 }}>Use the sidebar to navigate entities.</Typography>
    </Box>
  );
};

export default ModuleHome;
