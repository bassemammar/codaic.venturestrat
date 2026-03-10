import React, { useCallback, useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import { Rocket, Menu, X } from 'lucide-react';

import HeroSection from '../sections/HeroSection';
import StatsSection from '../sections/StatsSection';
import LivePreviewSection from '../sections/LivePreviewSection';
import HowItWorksSection from '../sections/HowItWorksSection';
import PricingSection from '../sections/PricingSection';
import FaqSection from '../sections/FaqSection';
import FooterSection from '../sections/FooterSection';

// ---------------------------------------------------------------------------
// Nav links
// ---------------------------------------------------------------------------

const navLinks = [
  { label: 'Features', anchor: '#features' },
  { label: 'Pricing', anchor: '#pricing' },
  { label: 'FAQ', anchor: '#faq' },
];

// ---------------------------------------------------------------------------
// Landing page component
// ---------------------------------------------------------------------------

const LandingPage: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Track scroll for appbar background
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Smooth scroll handler
  const handleAnchorClick = useCallback(
    (anchor: string) => {
      setDrawerOpen(false);
      const id = anchor.replace('#', '');
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    },
    [],
  );

  return (
    <Box sx={{ bgcolor: '#0a1929', minHeight: '100vh' }}>
      {/* ---- Navbar ---- */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          bgcolor: scrolled ? 'rgba(10,25,41,0.92)' : 'transparent',
          backdropFilter: scrolled ? 'blur(12px)' : 'none',
          borderBottom: scrolled ? '1px solid rgba(79,195,247,0.06)' : 'none',
          transition: 'background-color 0.3s, backdrop-filter 0.3s, border-bottom 0.3s',
        }}
      >
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ py: 0.5 }}>
            {/* Logo */}
            <Box
              sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 4, cursor: 'pointer' }}
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            >
              <Rocket size={22} color="#4fc3f7" />
              <Typography
                variant="h6"
                sx={{ fontWeight: 700, color: '#e3e8ef', letterSpacing: -0.5 }}
              >
                VentureStrat
              </Typography>
            </Box>

            {/* Desktop nav */}
            {!isMobile && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                {navLinks.map((link) => (
                  <Button
                    key={link.label}
                    onClick={() => handleAnchorClick(link.anchor)}
                    sx={{
                      color: '#8899aa',
                      textTransform: 'none',
                      fontWeight: 500,
                      fontSize: '0.875rem',
                      '&:hover': { color: '#4fc3f7', bgcolor: 'transparent' },
                    }}
                  >
                    {link.label}
                  </Button>
                ))}
              </Box>
            )}

            {/* Spacer on mobile */}
            {isMobile && <Box sx={{ flex: 1 }} />}

            {/* Right side CTAs */}
            {!isMobile && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Button
                  href="/login"
                  sx={{
                    color: '#8899aa',
                    textTransform: 'none',
                    fontWeight: 500,
                    fontSize: '0.875rem',
                    '&:hover': { color: '#4fc3f7', bgcolor: 'transparent' },
                  }}
                >
                  Log In
                </Button>
                <Button
                  variant="contained"
                  href="/login"
                  sx={{
                    bgcolor: '#4fc3f7',
                    color: '#0a1929',
                    textTransform: 'none',
                    fontWeight: 600,
                    px: 3,
                    borderRadius: 2,
                    '&:hover': { bgcolor: '#81d4fa' },
                  }}
                >
                  Get Started
                </Button>
              </Box>
            )}

            {/* Mobile hamburger */}
            {isMobile && (
              <IconButton
                onClick={() => setDrawerOpen(true)}
                sx={{ color: '#8899aa' }}
                aria-label="Open menu"
              >
                <Menu size={22} />
              </IconButton>
            )}
          </Toolbar>
        </Container>
      </AppBar>

      {/* ---- Mobile drawer ---- */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            width: 260,
            bgcolor: '#0d2137',
            borderLeft: '1px solid rgba(79,195,247,0.1)',
          },
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', p: 1.5 }}>
          <IconButton onClick={() => setDrawerOpen(false)} sx={{ color: '#8899aa' }}>
            <X size={20} />
          </IconButton>
        </Box>
        <List sx={{ px: 1 }}>
          {navLinks.map((link) => (
            <ListItemButton
              key={link.label}
              onClick={() => handleAnchorClick(link.anchor)}
              sx={{
                borderRadius: 1,
                mb: 0.5,
                '&:hover': { bgcolor: 'rgba(79,195,247,0.06)' },
              }}
            >
              <ListItemText
                primary={link.label}
                primaryTypographyProps={{ sx: { color: '#8899aa', fontWeight: 500 } }}
              />
            </ListItemButton>
          ))}
          <Box sx={{ px: 2, pt: 2 }}>
            <Button
              fullWidth
              href="/login"
              variant="outlined"
              sx={{
                mb: 1.5,
                borderColor: 'rgba(79,195,247,0.3)',
                color: '#4fc3f7',
                textTransform: 'none',
                fontWeight: 600,
                borderRadius: 2,
              }}
            >
              Log In
            </Button>
            <Button
              fullWidth
              href="/login"
              variant="contained"
              sx={{
                bgcolor: '#4fc3f7',
                color: '#0a1929',
                textTransform: 'none',
                fontWeight: 600,
                borderRadius: 2,
                '&:hover': { bgcolor: '#81d4fa' },
              }}
            >
              Get Started
            </Button>
          </Box>
        </List>
      </Drawer>

      {/* ---- Page sections ---- */}
      <HeroSection />
      <StatsSection />
      <LivePreviewSection />
      <HowItWorksSection />
      <PricingSection />
      <FaqSection />
      <FooterSection />
    </Box>
  );
};

export default LandingPage;
