import React from 'react';
import { Box, Typography, Paper, Divider } from '@mui/material';
import { Scale } from 'lucide-react';

const LegalPage: React.FC = () => {
  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', py: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
        <Scale size={24} color="#4f7df9" />
        <Typography variant="h4" fontWeight={700} sx={{ color: '#374151' }}>
          Legal
        </Typography>
      </Box>

      <Paper
        sx={{
          bgcolor: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: 2,
          p: 4,
          mb: 3,
        }}
      >
        <Typography variant="h6" fontWeight={600} sx={{ color: '#374151', mb: 2 }}>
          Terms of Service
        </Typography>
        <Typography variant="body2" sx={{ color: '#6b7280', lineHeight: 1.8 }}>
          By using VentureStrat, you agree to our terms and conditions. This platform
          provides tools for venture capital research, investor outreach, and CRM
          management. All data processed through VentureStrat is subject to our data
          handling policies and applicable regulations.
        </Typography>
        <Typography variant="body2" sx={{ color: '#6b7280', lineHeight: 1.8, mt: 2 }}>
          VentureStrat reserves the right to update these terms at any time. Users will
          be notified of material changes via email or in-app notification. Continued use
          of the platform after such changes constitutes acceptance of the updated terms.
        </Typography>
      </Paper>

      <Paper
        sx={{
          bgcolor: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: 2,
          p: 4,
        }}
      >
        <Typography variant="h6" fontWeight={600} sx={{ color: '#374151', mb: 2 }}>
          Privacy Policy
        </Typography>
        <Typography variant="body2" sx={{ color: '#6b7280', lineHeight: 1.8 }}>
          VentureStrat is committed to protecting your privacy. We collect only the
          information necessary to provide our services, including account credentials,
          usage data, and investor research preferences.
        </Typography>
        <Typography variant="body2" sx={{ color: '#6b7280', lineHeight: 1.8, mt: 2 }}>
          We do not sell your personal data to third parties. Investor data sourced
          through the platform is used solely for the purposes of your fundraising
          activities and CRM management within VentureStrat.
        </Typography>
      </Paper>
    </Box>
  );
};

export default LegalPage;
