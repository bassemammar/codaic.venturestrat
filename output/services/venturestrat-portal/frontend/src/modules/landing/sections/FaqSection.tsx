import React, { useEffect, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import { ChevronDown } from 'lucide-react';

// ---------------------------------------------------------------------------
// CSS keyframes
// ---------------------------------------------------------------------------

const keyframes = `
@keyframes faqFadeUp {
  from { opacity: 0; transform: translateY(16px); }
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
// FAQ data
// ---------------------------------------------------------------------------

const faqs = [
  {
    q: 'Where does the investor data come from?',
    a: 'Our database aggregates publicly available investor data from Crunchbase, LinkedIn, AngelList, and proprietary sources. All records are verified and deduplicated. We refresh data weekly to ensure accuracy.',
  },
  {
    q: 'Is there a free plan?',
    a: 'Yes! The free plan lets you search investors, view basic profiles, and send a limited number of outreach emails per day. Upgrade anytime to unlock unlimited access and AI-powered drafting.',
  },
  {
    q: 'How does AI outreach work?',
    a: 'When you select an investor, our AI analyzes their investment history, portfolio, and public posts to draft a personalized email. You can review, edit, and schedule it directly from the platform.',
  },
  {
    q: 'Can I integrate with my existing tools?',
    a: 'VentureStrat integrates with Gmail, Outlook, and major CRM platforms via our API. You can also export data as CSV for custom workflows. Zapier integration is on our roadmap.',
  },
  {
    q: 'Is my data secure?',
    a: 'Absolutely. We use AES-256 encryption at rest, TLS 1.3 in transit, and SOC 2-compliant infrastructure. Your outreach data and shortlists are private to your account and never shared.',
  },
  {
    q: 'How accurate are the email addresses?',
    a: 'We verify email deliverability before displaying them. Our database achieves a 92%+ deliverability rate. Invalid or bounced emails are automatically flagged and removed.',
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes, all paid plans are month-to-month with no long-term commitment. Cancel anytime from your account settings, and you keep access until the end of your billing cycle.',
  },
  {
    q: 'Do you offer a startup discount?',
    a: 'Yes! Early-stage startups (pre-Series A) can apply for our Founder Program, which provides a 50% discount on Pro and Scale plans for the first 6 months.',
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const FaqSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    injectKeyframes();
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.1 },
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <Box
      id="faq"
      ref={sectionRef}
      component="section"
      sx={{ bgcolor: '#0d2137', py: { xs: 8, md: 12 } }}
    >
      <Container maxWidth="md">
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
          Frequently Asked Questions
        </Typography>
        <Typography
          variant="body1"
          sx={{ textAlign: 'center', color: '#8899aa', mb: 6 }}
        >
          Everything you need to know about VentureStrat.
        </Typography>

        <Box>
          {faqs.map((faq, i) => (
            <Accordion
              key={i}
              disableGutters
              elevation={0}
              sx={{
                bgcolor: 'transparent',
                borderBottom: '1px solid rgba(79,195,247,0.08)',
                '&::before': { display: 'none' },
                animation: visible
                  ? `faqFadeUp 0.5s ease-out ${i * 0.06}s both`
                  : 'none',
                opacity: visible ? undefined : 0,
              }}
            >
              <AccordionSummary
                expandIcon={<ChevronDown size={18} color="#4fc3f7" />}
                sx={{
                  px: 0,
                  py: 1,
                  '& .MuiAccordionSummary-content': { my: 1.5 },
                }}
              >
                <Typography
                  variant="subtitle1"
                  sx={{ fontWeight: 600, color: '#e3e8ef' }}
                >
                  {faq.q}
                </Typography>
              </AccordionSummary>
              <AccordionDetails sx={{ px: 0, pb: 2.5 }}>
                <Typography variant="body2" sx={{ color: '#8899aa', lineHeight: 1.7 }}>
                  {faq.a}
                </Typography>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      </Container>
    </Box>
  );
};

export default FaqSection;
