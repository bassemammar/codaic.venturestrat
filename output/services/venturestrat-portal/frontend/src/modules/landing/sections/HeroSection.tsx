import React from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import { ArrowRight, Sparkles, Database, Globe, Zap } from 'lucide-react';

// ---------------------------------------------------------------------------
// CSS keyframes injected once
// ---------------------------------------------------------------------------

const keyframes = `
@keyframes heroGradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes heroPulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.05); }
}
@keyframes heroFadeUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
`;

let injected = false;
function injectKeyframes() {
  if (injected || typeof document === 'undefined') return;
  const style = document.createElement('style');
  style.textContent = keyframes;
  document.head.appendChild(style);
  injected = true;
}

// ---------------------------------------------------------------------------
// Stat pill data
// ---------------------------------------------------------------------------

const stats = [
  { icon: Database, label: '120K+ Investors', delay: '0.5s' },
  { icon: Globe, label: '18 Markets', delay: '0.65s' },
  { icon: Zap, label: 'AI-Powered Outreach', delay: '0.8s' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const HeroSection: React.FC = () => {
  React.useEffect(() => { injectKeyframes(); }, []);

  const scrollToPreview = () => {
    const el = document.getElementById('live-preview');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <Box
      component="section"
      sx={{
        position: 'relative',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        overflow: 'hidden',
        bgcolor: '#0a1929',
      }}
    >
      {/* Animated gradient background */}
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(135deg, rgba(79,195,247,0.12) 0%, rgba(124,77,255,0.10) 40%, rgba(79,195,247,0.06) 70%, rgba(124,77,255,0.12) 100%)',
          backgroundSize: '400% 400%',
          animation: 'heroGradientShift 12s ease infinite',
          zIndex: 0,
        }}
      />

      {/* Subtle radial orbs */}
      <Box
        sx={{
          position: 'absolute',
          top: '-20%',
          right: '-10%',
          width: 600,
          height: 600,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(79,195,247,0.08) 0%, transparent 70%)',
          animation: 'heroPulse 8s ease-in-out infinite',
          zIndex: 0,
        }}
      />
      <Box
        sx={{
          position: 'absolute',
          bottom: '-15%',
          left: '-10%',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(124,77,255,0.08) 0%, transparent 70%)',
          animation: 'heroPulse 10s ease-in-out infinite',
          animationDelay: '2s',
          zIndex: 0,
        }}
      />

      <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1, py: { xs: 10, md: 0 } }}>
        <Grid container spacing={4} sx={{ alignItems: 'center' }}>
          <Grid size={{ xs: 12, md: 8 }} offset={{ md: 2 }} sx={{ textAlign: 'center' }}>
            {/* Badge */}
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 0.75,
                px: 2,
                py: 0.5,
                mb: 3,
                borderRadius: 50,
                bgcolor: 'rgba(79,195,247,0.08)',
                border: '1px solid rgba(79,195,247,0.2)',
                animation: 'heroFadeUp 0.6s ease-out both',
              }}
            >
              <Sparkles size={14} color="#4fc3f7" />
              <Typography variant="caption" sx={{ color: '#4fc3f7', fontWeight: 600, letterSpacing: 0.5 }}>
                AI-Powered Fundraising Platform
              </Typography>
            </Box>

            {/* Headline */}
            <Typography
              variant="h1"
              sx={{
                fontSize: { xs: '2.5rem', sm: '3.25rem', md: '4rem' },
                fontWeight: 800,
                lineHeight: 1.1,
                mb: 3,
                color: '#e3e8ef',
                animation: 'heroFadeUp 0.6s ease-out 0.15s both',
              }}
            >
              Find Your Perfect{' '}
              <Box
                component="span"
                sx={{
                  background: 'linear-gradient(135deg, #4fc3f7, #7c4dff)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Investor
              </Box>
            </Typography>

            {/* Subheadline */}
            <Typography
              variant="h5"
              sx={{
                color: '#8899aa',
                fontWeight: 400,
                lineHeight: 1.6,
                maxWidth: 640,
                mx: 'auto',
                mb: 5,
                animation: 'heroFadeUp 0.6s ease-out 0.3s both',
              }}
            >
              Search 120,000+ verified investors across 18 markets.
              AI drafts your outreach. CRM tracks your pipeline. Close your round faster.
            </Typography>

            {/* CTAs */}
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2}
              sx={{
                justifyContent: 'center',
                mb: 6,
                animation: 'heroFadeUp 0.6s ease-out 0.45s both',
              }}
            >
              <Button
                variant="contained"
                size="large"
                href="/login"
                endIcon={<ArrowRight size={18} />}
                sx={{
                  px: 4,
                  py: 1.5,
                  fontSize: '1rem',
                  fontWeight: 600,
                  bgcolor: '#4fc3f7',
                  color: '#0a1929',
                  borderRadius: 2,
                  textTransform: 'none',
                  '&:hover': { bgcolor: '#81d4fa' },
                }}
              >
                Get Started Free
              </Button>
              <Button
                variant="outlined"
                size="large"
                onClick={scrollToPreview}
                sx={{
                  px: 4,
                  py: 1.5,
                  fontSize: '1rem',
                  fontWeight: 600,
                  borderColor: 'rgba(79,195,247,0.4)',
                  color: '#4fc3f7',
                  borderRadius: 2,
                  textTransform: 'none',
                  '&:hover': {
                    borderColor: '#4fc3f7',
                    bgcolor: 'rgba(79,195,247,0.06)',
                  },
                }}
              >
                See Live Data
              </Button>
            </Stack>

            {/* Stats row */}
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={3}
              sx={{ justifyContent: 'center', alignItems: 'center' }}
            >
              {stats.map(({ icon: Icon, label, delay }) => (
                <Box
                  key={label}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    animation: `heroFadeUp 0.6s ease-out ${delay} both`,
                  }}
                >
                  <Icon size={18} color="#4fc3f7" />
                  <Typography
                    variant="body2"
                    sx={{ color: '#8899aa', fontWeight: 500 }}
                  >
                    {label}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
};

export default HeroSection;
