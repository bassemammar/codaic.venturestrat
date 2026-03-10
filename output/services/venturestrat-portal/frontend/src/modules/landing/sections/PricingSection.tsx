import React, { useEffect, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import type { Plan } from '@bill/types/plan.types';
import PlanCards from '../../billing/components/PlanCards';

// ---------------------------------------------------------------------------
// CSS keyframes
// ---------------------------------------------------------------------------

const keyframes = `
@keyframes priceFadeUp {
  from { opacity: 0; transform: translateY(20px); }
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
// Fetch plans (public, no auth needed)
// ---------------------------------------------------------------------------

async function fetchPlans(): Promise<Plan[]> {
  const res = await axios.get('/api/v1/plans/', {
    params: { page_size: 200, is_active: true },
    headers: {
      'X-Tenant-ID': '00000000-0000-0000-0000-000000000000',
    },
  });
  const data = res.data;
  const items: Plan[] = Array.isArray(data) ? data : data.items ?? [];
  return items.filter((p) => p.is_active);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PricingSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  const { data: plans, isLoading } = useQuery<Plan[]>({
    queryKey: ['landing-plans'],
    queryFn: fetchPlans,
    staleTime: 10 * 60 * 1000,
  });

  useEffect(() => {
    injectKeyframes();
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.1 },
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const handleSelect = (plan: Plan) => {
    window.location.href = `/login?plan=${plan.code}`;
  };

  return (
    <Box
      id="pricing"
      ref={sectionRef}
      component="section"
      sx={{ bgcolor: '#0a1929', py: { xs: 8, md: 12 } }}
    >
      <Container maxWidth="lg">
        <Box
          sx={{
            textAlign: 'center',
            mb: 6,
            animation: visible ? 'priceFadeUp 0.6s ease-out both' : 'none',
            opacity: visible ? undefined : 0,
          }}
        >
          <Typography
            variant="h3"
            sx={{
              fontWeight: 700,
              color: '#e3e8ef',
              mb: 1.5,
              fontSize: { xs: '1.75rem', md: '2.25rem' },
            }}
          >
            Simple, Transparent Pricing
          </Typography>
          <Typography variant="body1" sx={{ color: '#8899aa', maxWidth: 480, mx: 'auto' }}>
            Start free. Upgrade when you need more. No hidden fees, cancel anytime.
          </Typography>
        </Box>

        <Box
          sx={{
            animation: visible ? 'priceFadeUp 0.6s ease-out 0.2s both' : 'none',
            opacity: visible ? undefined : 0,
          }}
        >
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
              <CircularProgress size={32} sx={{ color: '#4fc3f7' }} />
            </Box>
          ) : plans && plans.length > 0 ? (
            <PlanCards
              plans={plans}
              currentPlanId={null}
              currentPrice={0}
              onSelect={handleSelect}
            />
          ) : (
            <Typography
              variant="body1"
              sx={{ textAlign: 'center', color: '#6b7d8e', py: 6 }}
            >
              Pricing plans coming soon.
            </Typography>
          )}
        </Box>
      </Container>
    </Box>
  );
};

export default PricingSection;
