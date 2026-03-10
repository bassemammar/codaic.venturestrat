/**
 * Home Page Component
 *
 * Landing page for legal with:
 * - Welcome section with project overview
 * - Navigation cards for all entity management pages
 * - Responsive grid layout
 * - Quick access to common actions
 *
 * @description Home page for legal
 * @generated 2026-03-10T20:43:55.908960Z
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
    path: '/contact-persons',
    title: 'Contactpersons',
    description: 'Individual associated with a legal entity — founder, director, signatory, or counterparty',
    icon: <ListIcon />,
  },
  {
    path: '/document-parties',
    title: 'Documentparties',
    description: 'Links a legal document to its parties (entity + signatory) with role designation',
    icon: <ListIcon />,
  },
  {
    path: '/document-templates',
    title: 'Documenttemplates',
    description: 'Legal document template definition — NDA, founders agreement, SAFE, employment, etc.',
    icon: <ListIcon />,
  },
  {
    path: '/equity-grants',
    title: 'Equitygrants',
    description: 'Cap table entry — equity holding in a legal entity with share class and valuation',
    icon: <ListIcon />,
  },
  {
    path: '/investment-terms',
    title: 'Investmentterms',
    description: 'SAFE or priced round investment terms linked to a legal entity and investor person',
    icon: <ListIcon />,
  },
  {
    path: '/legal-addresses',
    title: 'Legaladdresses',
    description: 'Physical address for legal entities and persons with jurisdiction classification',
    icon: <ListIcon />,
  },
  {
    path: '/legal-documents',
    title: 'Legaldocuments',
    description: 'Generated legal document with full lifecycle tracking, template reference, and party links',
    icon: <ListIcon />,
  },
  {
    path: '/legal-entities',
    title: 'Legalentities',
    description: 'Legal entity (company or organization) that acts as party in legal documents',
    icon: <ListIcon />,
  },
  {
    path: '/template-clauses',
    title: 'Templateclauses',
    description: 'Clause library entry with conditional variants (A/B/C/D) for legal document generation',
    icon: <ListIcon />,
  },
  {
    path: '/vesting-schedules',
    title: 'Vestingschedules',
    description: 'Vesting schedule for equity grants — cliff period, total period, and acceleration triggers',
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
          Welcome to legal
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Frontend for legal
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
                  Contactpersons
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
                  Documentparties
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
                  Documenttemplates
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
                  Equitygrants
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
