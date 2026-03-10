import React from 'react';
import { Box, Typography, Paper, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import { HelpCircle, ChevronDown } from 'lucide-react';

const FAQ_ITEMS = [
  {
    question: 'How do I search for investors?',
    answer:
      'Navigate to Fundraising > Investor Directory from the sidebar. Use the search bar and filters to find investors by name, market focus, investment stage, or ticket size.',
  },
  {
    question: 'How does the CRM Pipeline work?',
    answer:
      'The CRM Pipeline is a Kanban board that tracks your fundraising progress. Drag investor cards between stages (e.g., Researched, Contacted, Meeting Scheduled, Term Sheet, Closed). Access it via Fundraising > CRM Pipeline.',
  },
  {
    question: 'How do I send emails to investors?',
    answer:
      'Go to Mail from the sidebar to access the email client. You can compose emails, use templates, and track responses. Connect your email account first in Settings > Integrations.',
  },
  {
    question: 'How do I manage my subscription?',
    answer:
      'Click Subscriptions in the sidebar to view your current plan, usage, and billing details. You can upgrade, downgrade, or manage payment methods from there.',
  },
  {
    question: 'How do I connect my email account?',
    answer:
      'Go to Settings and look for the Integrations section. You can connect Google or Microsoft email accounts via OAuth for sending and receiving emails directly within VentureStrat.',
  },
  {
    question: 'Who can I contact for support?',
    answer:
      'For technical support or feature requests, reach out to our team at support@venturestrat.ai. We aim to respond within 24 hours on business days.',
  },
];

const HelpPage: React.FC = () => {
  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', py: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
        <HelpCircle size={24} color="#4f7df9" />
        <Typography variant="h4" fontWeight={700} sx={{ color: '#374151' }}>
          Help Center
        </Typography>
      </Box>

      <Typography variant="body1" sx={{ color: '#6b7280', mb: 4 }}>
        Find answers to common questions about using VentureStrat. If you cannot find
        what you are looking for, contact our support team.
      </Typography>

      <Paper
        sx={{
          bgcolor: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        <Typography
          variant="h6"
          fontWeight={600}
          sx={{ color: '#374151', p: 3, pb: 1 }}
        >
          Frequently Asked Questions
        </Typography>
        {FAQ_ITEMS.map((item, idx) => (
          <Accordion
            key={idx}
            disableGutters
            elevation={0}
            sx={{
              bgcolor: 'transparent',
              '&:before': { display: 'none' },
              borderTop: idx > 0 ? '1px solid #e5e7eb' : 'none',
            }}
          >
            <AccordionSummary
              expandIcon={<ChevronDown size={16} color="#6b7280" />}
              sx={{ px: 3, '&:hover': { bgcolor: 'rgba(79, 195, 247, 0.04)' } }}
            >
              <Typography variant="body1" fontWeight={500} sx={{ color: '#c5cdd8' }}>
                {item.question}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ px: 3, pb: 2 }}>
              <Typography variant="body2" sx={{ color: '#6b7280', lineHeight: 1.8 }}>
                {item.answer}
              </Typography>
            </AccordionDetails>
          </Accordion>
        ))}
      </Paper>
    </Box>
  );
};

export default HelpPage;
