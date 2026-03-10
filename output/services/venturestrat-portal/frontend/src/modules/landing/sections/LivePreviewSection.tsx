import React, { useCallback, useEffect, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import Skeleton from '@mui/material/Skeleton';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import { RefreshCw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useInvestorLivePreview } from '../../investor/hooks/useInvestorLivePreview';
import InvestorCard from '../../investor/components/InvestorCard';

// ---------------------------------------------------------------------------
// CSS keyframes
// ---------------------------------------------------------------------------

const keyframes = `
@keyframes previewFadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes spinRefresh {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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
// Skeleton placeholder
// ---------------------------------------------------------------------------

const CardSkeleton: React.FC = () => (
  <Card sx={{ bgcolor: '#0d2137', border: '1px solid rgba(79,195,247,0.08)' }}>
    <CardContent sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', gap: 1.5, mb: 1.5 }}>
        <Skeleton variant="circular" width={44} height={44} sx={{ bgcolor: 'rgba(79,195,247,0.08)' }} />
        <Box sx={{ flex: 1 }}>
          <Skeleton variant="text" width="70%" sx={{ bgcolor: 'rgba(79,195,247,0.08)' }} />
          <Skeleton variant="text" width="50%" sx={{ bgcolor: 'rgba(79,195,247,0.08)' }} />
        </Box>
      </Box>
      <Skeleton variant="text" width="40%" sx={{ bgcolor: 'rgba(79,195,247,0.08)' }} />
    </CardContent>
  </Card>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const LivePreviewSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const queryClient = useQueryClient();
  const { data: investors, isLoading, isFetching } = useInvestorLivePreview();

  useEffect(() => {
    injectKeyframes();
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 },
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ['investor-live-preview'] });
    // brief delay so the spin animation is visible
    setTimeout(() => setRefreshing(false), 600);
  }, [queryClient]);

  const showSkeletons = isLoading || (!investors && isFetching);

  return (
    <Box
      id="live-preview"
      ref={sectionRef}
      component="section"
      sx={{ bgcolor: '#0a1929', py: { xs: 8, md: 12 } }}
    >
      <Container maxWidth="lg">
        {/* Header */}
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography
            variant="h3"
            sx={{
              fontWeight: 700,
              color: '#e3e8ef',
              mb: 1.5,
              fontSize: { xs: '1.75rem', md: '2.25rem' },
            }}
          >
            Real Investors,{' '}
            <Box
              component="span"
              sx={{
                background: 'linear-gradient(135deg, #4fc3f7, #7c4dff)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Live Data
            </Box>
          </Typography>
          <Typography variant="body1" sx={{ color: '#8899aa', maxWidth: 520, mx: 'auto', mb: 3 }}>
            Every card below is a real investor from our database. Hit refresh to see a new set.
          </Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={
              <RefreshCw
                size={16}
                style={{
                  animation: refreshing || isFetching ? 'spinRefresh 0.6s linear infinite' : 'none',
                }}
              />
            }
            onClick={handleRefresh}
            disabled={refreshing || isFetching}
            sx={{
              borderColor: 'rgba(79,195,247,0.3)',
              color: '#4fc3f7',
              textTransform: 'none',
              fontWeight: 600,
              borderRadius: 2,
              '&:hover': {
                borderColor: '#4fc3f7',
                bgcolor: 'rgba(79,195,247,0.06)',
              },
            }}
          >
            Refresh
          </Button>
        </Box>

        {/* Cards grid */}
        <Grid container spacing={2.5}>
          {showSkeletons
            ? Array.from({ length: 6 }).map((_, i) => (
                <Grid key={i} size={{ xs: 12, sm: 6, md: 4 }}>
                  <CardSkeleton />
                </Grid>
              ))
            : (investors ?? []).slice(0, 6).map((investor, i) => (
                <Grid
                  key={investor.id}
                  size={{ xs: 12, sm: 6, md: 4 }}
                  sx={{
                    animation: visible
                      ? `previewFadeIn 0.5s ease-out ${i * 0.08}s both`
                      : 'none',
                    opacity: visible ? undefined : 0,
                  }}
                >
                  <InvestorCard investor={investor} />
                </Grid>
              ))}
        </Grid>

        {/* Bottom CTA */}
        <Box sx={{ textAlign: 'center', mt: 5 }}>
          <Typography variant="body2" sx={{ color: '#6b7d8e', mb: 2 }}>
            Want full access to all 120,000+ investors?
          </Typography>
          <Button
            variant="contained"
            href="/login"
            sx={{
              px: 4,
              py: 1.25,
              bgcolor: '#4fc3f7',
              color: '#0a1929',
              fontWeight: 600,
              textTransform: 'none',
              borderRadius: 2,
              '&:hover': { bgcolor: '#81d4fa' },
            }}
          >
            Sign Up Free
          </Button>
        </Box>
      </Container>
    </Box>
  );
};

export default LivePreviewSection;
