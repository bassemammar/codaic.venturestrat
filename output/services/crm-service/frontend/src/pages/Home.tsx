/**
 * Home Page Component
 *
 * Landing page for crm with:
 * - Welcome section with project overview
 * - Navigation cards for all entity management pages
 * - Responsive grid layout
 * - Quick access to common actions
 *
 * @description Home page for crm
 * @generated 2026-03-10T13:09:26.115903Z
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Grid,
  Typography,
  useTheme,
  Paper,
} from '@mui/material';
import {
  List as ListIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

/**
 * Navigation card item definition
 */
interface NavCardItem {
  /** Route path to navigate to */
  path: string;
  /** Display title */
  title: string;
  /** Description text */
  description: string;
  /** Icon component */
  icon: React.ReactElement;
  /** Optional color override */
  color?: string;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Entity navigation cards configuration
 *
 * Generated from entity definitions for quick navigation
 * to each entity's management page.
 */
const ENTITY_CARDS: NavCardItem[] = [
  {
    path: '/activities',
    title: 'Activities',
    description: 'Outreach activity touchpoint on a shortlisted investor',
    icon: <ListIcon />,
  },
  {
    path: '/pipeline-stages',
    title: 'Pipelinestages',
    description: 'CRM pipeline stage for investor shortlisting',
    icon: <ListIcon />,
  },
  {
    path: '/shortlists',
    title: 'Shortlists',
    description: 'User\'s investor pipeline — tracks shortlisted investors with CRM status',
    icon: <ListIcon />,
  },
  {
    path: '/shortlist-tags',
    title: 'Shortlisttags',
    description: 'Many-to-many junction between shortlists and tags',
    icon: <ListIcon />,
  },
  {
    path: '/tags',
    title: 'Tags',
    description: 'Tag for categorizing shortlisted investors',
    icon: <ListIcon />,
  },
];

// ============================================================================
// Component
// ============================================================================

/**
 * Home Page Component
 *
 * Renders the application landing page with navigation cards
 * for all entity management sections.
 */
export function Home(): React.ReactElement {
  const theme = useTheme();
  const navigate = useNavigate();

  /**
   * Handle navigation card click
   */
  const handleCardClick = (path: string) => {
    navigate(path);
  };

  return (
    <Box>
      {/* Welcome Section */}
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome to crm
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Frontend for crm
        </Typography>
      </Box>

      {/* Quick Stats Section */}
      <Box mb={4}>
        <Typography variant="h6" gutterBottom>
          Overview
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper
              elevation={0}
sx={{
                p: 2,
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
                borderRadius: 2,
              }}            >
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <ListIcon
                  sx={ { color: theme.palette.primary.main, fontSize: 20 } }
                />
                <Typography variant="subtitle2" color="text.secondary">
                  Activities
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>
                {/* Stats would be loaded from API */}
                --
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper
              elevation={0}
sx={{
                p: 2,
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
                borderRadius: 2,
              }}            >
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <ListIcon
                  sx={ { color: theme.palette.primary.main, fontSize: 20 } }
                />
                <Typography variant="subtitle2" color="text.secondary">
                  Pipelinestages
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>
                {/* Stats would be loaded from API */}
                --
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper
              elevation={0}
sx={{
                p: 2,
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
                borderRadius: 2,
              }}            >
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <ListIcon
                  sx={ { color: theme.palette.primary.main, fontSize: 20 } }
                />
                <Typography variant="subtitle2" color="text.secondary">
                  Shortlists
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>
                {/* Stats would be loaded from API */}
                --
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper
              elevation={0}
sx={{
                p: 2,
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
                borderRadius: 2,
              }}            >
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <ListIcon
                  sx={ { color: theme.palette.primary.main, fontSize: 20 } }
                />
                <Typography variant="subtitle2" color="text.secondary">
                  Shortlisttags
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>
                {/* Stats would be loaded from API */}
                --
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>

      {/* Entity Navigation Cards */}
      <Box>
        <Typography variant="h6" gutterBottom>
          Manage Entities
        </Typography>
        <Grid container spacing={3}>
          {ENTITY_CARDS.map((card) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={card.path}>
              <Card
                variant="outlined"
sx={{
                  height: '100%',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    borderColor: theme.palette.primary.main,
                    boxShadow: `0 4px 12px ${theme.palette.primary.main}1A`,
                    transform: 'translateY(-2px)',
                  },
                }}              >
                <CardActionArea
                  onClick={() => handleCardClick(card.path)}
                  sx={ { height: '100%' } }
                >
                  <CardContent>
                    <Box
                      display="flex"
                      alignItems="flex-start"
                      justifyContent="space-between"
                    >
                      <Box
sx={{
                          p: 1,
                          borderRadius: 1,
                          backgroundColor: `${theme.palette.primary.main}14`,
                          color: theme.palette.primary.main,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}                      >
                        {card.icon}
                      </Box>
                      <ArrowForwardIcon
sx={{
                          color: theme.palette.text.disabled,
                          fontSize: 20,
                        }}                      />
                    </Box>
                    <Typography
                      variant="h6"
                      component="h2"
                      sx={ { mt: 2, mb: 0.5 } }
                    >
                      {card.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {card.description}
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

    </Box>
  );
}

export default Home;
