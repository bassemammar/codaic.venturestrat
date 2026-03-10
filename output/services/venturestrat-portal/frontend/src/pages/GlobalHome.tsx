import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Card, CardActionArea, CardContent, Grid, Typography } from '@mui/material';
import { MODULE_LIST } from '../theme/moduleColors';

const GlobalHome: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto', py: 4 }}>
      <Typography variant="h4" fontWeight={700} sx={{ mb: 1, color: '#374151' }}>VentureStrat</Typography>
      <Typography variant="body1" sx={{ mb: 4, color: '#6b7280' }}>Select a module to get started</Typography>
      <Grid container spacing={2}>
        {MODULE_LIST.map((mod) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={mod.id}>
            <Card sx={{ bgcolor: '#ffffff', border: '1px solid #e5e7eb', '&:hover': { borderColor: mod.accent } }}>
              <CardActionArea onClick={() => navigate(`/${mod.id}`)} sx={{ p: 2 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight={600} sx={{ color: mod.accent, mb: 0.5 }}>{mod.label}</Typography>
                  <Typography variant="body2" sx={{ color: '#6b7280' }}>{mod.description}</Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default GlobalHome;
