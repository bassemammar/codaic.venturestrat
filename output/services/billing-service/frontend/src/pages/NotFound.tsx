/**
 * NotFound Page Component
 *
 * Displays a 404 error message when a route is not found.
 *
 * @generated
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Typography } from '@mui/material';
import { Home as HomeIcon } from '@mui/icons-material';

/**
 * NotFound Component
 *
 * Renders a 404 error page with a link back to the home page.
 */
export function NotFound(): React.ReactElement {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        textAlign: 'center',
        p: 3,
      }}
    >
      <Typography variant="h1" component="h1" sx={{ fontSize: '6rem', fontWeight: 700, color: 'text.secondary' }}>
        404
      </Typography>
      <Typography variant="h5" component="h2" gutterBottom>
        Page Not Found
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        The page you are looking for does not exist or has been moved.
      </Typography>
      <Button
        variant="contained"
        startIcon={<HomeIcon />}
        onClick={() => navigate('/')}
      >
        Go to Home
      </Button>
    </Box>
  );
}

export default NotFound;
