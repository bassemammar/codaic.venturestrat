import React from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Link from '@mui/material/Link';
import IconButton from '@mui/material/IconButton';
import Divider from '@mui/material/Divider';
import { Twitter, Linkedin, Github, Rocket } from 'lucide-react';

// ---------------------------------------------------------------------------
// Link groups
// ---------------------------------------------------------------------------

const productLinks = [
  { label: 'Features', href: '#features' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'FAQ', href: '#faq' },
  { label: 'Live Preview', href: '#live-preview' },
];

const companyLinks = [
  { label: 'About', href: '#' },
  { label: 'Blog', href: '#' },
  { label: 'Careers', href: '#' },
  { label: 'Contact', href: '#' },
];

const legalLinks = [
  { label: 'Privacy Policy', href: '#' },
  { label: 'Terms of Service', href: '#' },
  { label: 'Cookie Policy', href: '#' },
];

const socialLinks = [
  { icon: Twitter, href: '#', label: 'Twitter' },
  { icon: Linkedin, href: '#', label: 'LinkedIn' },
  { icon: Github, href: '#', label: 'GitHub' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const FooterSection: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <Box
      component="footer"
      sx={{ bgcolor: '#071320', pt: { xs: 6, md: 8 }, pb: { xs: 3, md: 4 } }}
    >
      <Container maxWidth="lg">
        <Grid container spacing={4} sx={{ mb: 6 }}>
          {/* Brand column */}
          <Grid size={{ xs: 12, md: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Rocket size={22} color="#4fc3f7" />
              <Typography
                variant="h6"
                sx={{ fontWeight: 700, color: '#e3e8ef', letterSpacing: -0.5 }}
              >
                VentureStrat
              </Typography>
            </Box>
            <Typography
              variant="body2"
              sx={{ color: '#6b7d8e', lineHeight: 1.7, maxWidth: 300, mb: 2.5 }}
            >
              The AI-powered fundraising platform. Find investors, craft outreach, and manage your pipeline -- all in one place.
            </Typography>
            <Stack direction="row" spacing={0.5}>
              {socialLinks.map(({ icon: Icon, href, label }) => (
                <IconButton
                  key={label}
                  href={href}
                  aria-label={label}
                  size="small"
                  sx={{
                    color: '#6b7d8e',
                    '&:hover': { color: '#4fc3f7', bgcolor: 'rgba(79,195,247,0.08)' },
                  }}
                >
                  <Icon size={18} />
                </IconButton>
              ))}
            </Stack>
          </Grid>

          {/* Product links */}
          <Grid size={{ xs: 6, sm: 4, md: 2 }} offset={{ md: 1 }}>
            <Typography
              variant="overline"
              sx={{ color: '#8899aa', fontWeight: 600, mb: 2, display: 'block', letterSpacing: 1 }}
            >
              Product
            </Typography>
            <Stack spacing={1.25}>
              {productLinks.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  underline="none"
                  sx={{
                    color: '#6b7d8e',
                    fontSize: '0.875rem',
                    transition: 'color 0.15s',
                    '&:hover': { color: '#4fc3f7' },
                  }}
                >
                  {link.label}
                </Link>
              ))}
            </Stack>
          </Grid>

          {/* Company links */}
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Typography
              variant="overline"
              sx={{ color: '#8899aa', fontWeight: 600, mb: 2, display: 'block', letterSpacing: 1 }}
            >
              Company
            </Typography>
            <Stack spacing={1.25}>
              {companyLinks.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  underline="none"
                  sx={{
                    color: '#6b7d8e',
                    fontSize: '0.875rem',
                    transition: 'color 0.15s',
                    '&:hover': { color: '#4fc3f7' },
                  }}
                >
                  {link.label}
                </Link>
              ))}
            </Stack>
          </Grid>

          {/* Legal links */}
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Typography
              variant="overline"
              sx={{ color: '#8899aa', fontWeight: 600, mb: 2, display: 'block', letterSpacing: 1 }}
            >
              Legal
            </Typography>
            <Stack spacing={1.25}>
              {legalLinks.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  underline="none"
                  sx={{
                    color: '#6b7d8e',
                    fontSize: '0.875rem',
                    transition: 'color 0.15s',
                    '&:hover': { color: '#4fc3f7' },
                  }}
                >
                  {link.label}
                </Link>
              ))}
            </Stack>
          </Grid>
        </Grid>

        <Divider sx={{ borderColor: 'rgba(79,195,247,0.06)', mb: 3 }} />

        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Typography variant="caption" sx={{ color: '#4a5968' }}>
            {currentYear} VentureStrat. All rights reserved.
          </Typography>
          <Typography variant="caption" sx={{ color: '#4a5968' }}>
            Built with care for founders everywhere.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default FooterSection;
