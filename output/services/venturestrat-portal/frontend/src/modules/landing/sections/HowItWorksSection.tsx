import React, { useEffect, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import { Search, ListChecks, Send, Handshake } from 'lucide-react';

// ---------------------------------------------------------------------------
// CSS keyframes
// ---------------------------------------------------------------------------

const keyframes = `
@keyframes hiwFadeUp {
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
// Steps
// ---------------------------------------------------------------------------

const steps = [
  {
    icon: Search,
    title: 'Search',
    description: 'Filter 120K+ investors by stage, type, market, and location. Find the perfect match in seconds.',
    color: '#4fc3f7',
  },
  {
    icon: ListChecks,
    title: 'Shortlist',
    description: 'Save investors to curated lists. Tag, compare, and prioritize your top targets with Kanban boards.',
    color: '#7c4dff',
  },
  {
    icon: Send,
    title: 'Outreach',
    description: 'AI drafts personalized emails for each investor. Schedule sends, track opens, and automate follow-ups.',
    color: '#4fc3f7',
  },
  {
    icon: Handshake,
    title: 'Close',
    description: 'Track conversations in your CRM pipeline. Move deals through stages from intro to term sheet.',
    color: '#7c4dff',
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const HowItWorksSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    injectKeyframes();
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 },
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <Box
      id="features"
      ref={sectionRef}
      component="section"
      sx={{ bgcolor: '#0d2137', py: { xs: 8, md: 12 } }}
    >
      <Container maxWidth="lg">
        <Typography
          variant="h3"
          sx={{
            textAlign: 'center',
            fontWeight: 700,
            color: '#e3e8ef',
            mb: 1.5,
            fontSize: { xs: '1.75rem', md: '2.25rem' },
          }}
        >
          How It Works
        </Typography>
        <Typography
          variant="body1"
          sx={{ textAlign: 'center', color: '#8899aa', maxWidth: 480, mx: 'auto', mb: 8 }}
        >
          Four simple steps from discovery to deal. Our platform handles the heavy lifting.
        </Typography>

        {/* Steps with connector line */}
        <Box sx={{ position: 'relative' }}>
          {/* Horizontal connector visible on md+ */}
          <Box
            sx={{
              display: { xs: 'none', md: 'block' },
              position: 'absolute',
              top: 48,
              left: '15%',
              right: '15%',
              height: 2,
              background: 'linear-gradient(90deg, #4fc3f7, #7c4dff, #4fc3f7, #7c4dff)',
              opacity: 0.25,
              borderRadius: 1,
            }}
          />

          <Grid container spacing={4}>
            {steps.map((step, i) => {
              const Icon = step.icon;
              return (
                <Grid key={step.title} size={{ xs: 12, sm: 6, md: 3 }}>
                  <Box
                    sx={{
                      textAlign: 'center',
                      position: 'relative',
                      animation: visible
                        ? `hiwFadeUp 0.6s ease-out ${i * 0.15}s both`
                        : 'none',
                      opacity: visible ? undefined : 0,
                    }}
                  >
                    {/* Step number + icon circle */}
                    <Box
                      sx={{
                        width: 80,
                        height: 80,
                        mx: 'auto',
                        mb: 3,
                        borderRadius: '50%',
                        bgcolor: `${step.color}14`,
                        border: `2px solid ${step.color}33`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        position: 'relative',
                      }}
                    >
                      <Icon size={32} color={step.color} />
                      {/* Step number badge */}
                      <Box
                        sx={{
                          position: 'absolute',
                          top: -6,
                          right: -6,
                          width: 28,
                          height: 28,
                          borderRadius: '50%',
                          bgcolor: step.color,
                          color: '#0a1929',
                          fontSize: 13,
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {i + 1}
                      </Box>
                    </Box>

                    <Typography
                      variant="h6"
                      sx={{ fontWeight: 700, color: '#e3e8ef', mb: 1 }}
                    >
                      {step.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ color: '#8899aa', lineHeight: 1.7, maxWidth: 260, mx: 'auto' }}
                    >
                      {step.description}
                    </Typography>
                  </Box>
                </Grid>
              );
            })}
          </Grid>
        </Box>
      </Container>
    </Box>
  );
};

export default HowItWorksSection;
