import React, { useCallback, useEffect, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import { Database, Globe, Mail, Star } from 'lucide-react';

// ---------------------------------------------------------------------------
// CSS keyframes
// ---------------------------------------------------------------------------

const keyframes = `
@keyframes statFadeUp {
  from { opacity: 0; transform: translateY(24px); }
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
// Count-up hook
// ---------------------------------------------------------------------------

function useCountUp(end: number, duration: number, startCounting: boolean, decimals = 0) {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number | null>(null);

  const animate = useCallback(() => {
    const startTime = performance.now();
    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(parseFloat((eased * end).toFixed(decimals)));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    };
    rafRef.current = requestAnimationFrame(step);
  }, [end, duration, decimals]);

  useEffect(() => {
    if (!startCounting) return;
    animate();
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [startCounting, animate]);

  return value;
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

interface StatItem {
  icon: React.FC<{ size?: number | string; color?: string }>;
  value: number;
  suffix: string;
  label: string;
  decimals?: number;
  color: string;
}

const statItems: StatItem[] = [
  { icon: Database, value: 120, suffix: 'K+', label: 'Verified Investors', color: '#4fc3f7' },
  { icon: Globe, value: 18, suffix: '+', label: 'Global Markets', color: '#7c4dff' },
  { icon: Mail, value: 50, suffix: 'K+', label: 'Emails Sent', color: '#4fc3f7' },
  { icon: Star, value: 4.8, suffix: '/5', label: 'User Rating', decimals: 1, color: '#7c4dff' },
];

// ---------------------------------------------------------------------------
// Single stat card
// ---------------------------------------------------------------------------

const StatCard: React.FC<{ item: StatItem; index: number; visible: boolean }> = ({
  item,
  index,
  visible,
}) => {
  const count = useCountUp(item.value, 2000, visible, item.decimals ?? 0);
  const Icon = item.icon;

  return (
    <Box
      sx={{
        textAlign: 'center',
        p: 4,
        borderRadius: 2,
        bgcolor: 'rgba(13,33,55,0.6)',
        border: '1px solid rgba(79,195,247,0.08)',
        animation: visible ? `statFadeUp 0.6s ease-out ${index * 0.15}s both` : 'none',
        opacity: visible ? undefined : 0,
        transition: 'border-color 0.2s, box-shadow 0.2s',
        '&:hover': {
          borderColor: 'rgba(79,195,247,0.25)',
          boxShadow: '0 4px 24px rgba(79,195,247,0.06)',
        },
      }}
    >
      <Box
        sx={{
          display: 'inline-flex',
          p: 1.5,
          borderRadius: '50%',
          bgcolor: `${item.color}14`,
          mb: 2,
        }}
      >
        <Icon size={24} color={item.color} />
      </Box>
      <Typography
        variant="h3"
        sx={{
          fontWeight: 800,
          fontSize: { xs: '2rem', md: '2.5rem' },
          color: '#e3e8ef',
          mb: 0.5,
        }}
      >
        {item.decimals ? count.toFixed(item.decimals) : Math.floor(count)}
        {item.suffix}
      </Typography>
      <Typography variant="body1" sx={{ color: '#8899aa', fontWeight: 500 }}>
        {item.label}
      </Typography>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Section
// ---------------------------------------------------------------------------

const StatsSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    injectKeyframes();
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.2 },
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <Box
      ref={sectionRef}
      component="section"
      sx={{ bgcolor: '#0d2137', py: { xs: 8, md: 12 } }}
    >
      <Container maxWidth="lg">
        <Typography
          variant="h4"
          sx={{
            textAlign: 'center',
            fontWeight: 700,
            color: '#e3e8ef',
            mb: 6,
          }}
        >
          Trusted by Founders Worldwide
        </Typography>
        <Grid container spacing={3}>
          {statItems.map((item, i) => (
            <Grid key={item.label} size={{ xs: 6, md: 3 }}>
              <StatCard item={item} index={i} visible={visible} />
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};

export default StatsSection;
