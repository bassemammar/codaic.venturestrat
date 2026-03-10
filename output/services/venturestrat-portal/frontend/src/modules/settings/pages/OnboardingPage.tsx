import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import { Mail, Rocket, ArrowRight, SkipForward } from 'lucide-react';
import type { Plan } from '@bill/types/plan.types';
import { usePlans } from '../../billing/hooks/usePlans';
import PlanCards from '../../billing/components/PlanCards';

// ---------------------------------------------------------------------------
// Steps
// ---------------------------------------------------------------------------

const STEPS = ['Company Info', 'Connect Email', 'Select Plan', 'Welcome'];

const COMPANY_SIZES = [
  { value: '1', label: 'Just me' },
  { value: '2-10', label: '2-10 people' },
  { value: '11-50', label: '11-50 people' },
  { value: '51-200', label: '51-200 people' },
  { value: '200+', label: '200+ people' },
];

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

interface CompanyInfo {
  companyName: string;
  role: string;
  companySize: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: plans = [] } = usePlans();

  const [activeStep, setActiveStep] = useState(0);
  const [company, setCompany] = useState<CompanyInfo>({
    companyName: '',
    role: '',
    companySize: '',
  });

  const handleNext = () => {
    setActiveStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  };

  const handleBack = () => {
    setActiveStep((prev) => Math.max(prev - 1, 0));
  };

  const handleSelectPlan = (plan: Plan) => {
    // For free plan, skip payment and go to welcome
    if (plan.price_monthly === 0) {
      handleNext();
      return;
    }
    // For paid plans, redirect to payment, which returns to billing/success
    navigate(`/billing/payment?plan_id=${plan.id}`);
  };

  const handleComplete = () => {
    navigate('/dashboard');
  };

  const canProceedStep0 =
    company.companyName.trim() !== '' &&
    company.role.trim() !== '' &&
    company.companySize !== '';

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: '#f9fafb',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        p: { xs: 2, md: 4 },
        pt: { xs: 4, md: 8 },
      }}
    >
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, textAlign: 'center' }}>
        Welcome to VentureStrat
      </Typography>
      <Typography
        variant="body1"
        sx={{ color: '#6b7280', mb: 5, textAlign: 'center', maxWidth: 500 }}
      >
        Let's get you set up in a few quick steps.
      </Typography>

      <Stepper
        activeStep={activeStep}
        alternativeLabel
        sx={{
          width: '100%',
          maxWidth: 600,
          mb: 5,
          '& .MuiStepLabel-label': { color: '#6b7280' },
          '& .MuiStepLabel-label.Mui-active': { color: '#374151' },
          '& .MuiStepLabel-label.Mui-completed': { color: '#66bb6a' },
        }}
      >
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      <Box sx={{ width: '100%', maxWidth: 800 }}>
        {/* Step 0: Company Info */}
        {activeStep === 0 && (
          <Paper
            sx={{
              p: 4,
              bgcolor: '#ffffff',
              border: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
              Tell us about your company
            </Typography>
            <Stack spacing={2.5} sx={{ maxWidth: 400 }}>
              <TextField
                label="Company Name"
                value={company.companyName}
                onChange={(e) =>
                  setCompany((prev) => ({ ...prev, companyName: e.target.value }))
                }
                fullWidth
                size="small"
                placeholder="Acme Corp"
              />
              <TextField
                label="Your Role"
                value={company.role}
                onChange={(e) =>
                  setCompany((prev) => ({ ...prev, role: e.target.value }))
                }
                fullWidth
                size="small"
                placeholder="Founder, CEO, VP Sales..."
              />
              <TextField
                label="Company Size"
                select
                value={company.companySize}
                onChange={(e) =>
                  setCompany((prev) => ({ ...prev, companySize: e.target.value }))
                }
                fullWidth
                size="small"
              >
                {COMPANY_SIZES.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4 }}>
              <Button
                variant="contained"
                onClick={handleNext}
                disabled={!canProceedStep0}
                endIcon={<ArrowRight size={16} />}
                sx={{
                  bgcolor: '#4f7df9',
                  color: '#f9fafb',
                  fontWeight: 600,
                  '&:hover': { bgcolor: '#4f7df9', opacity: 0.9 },
                }}
              >
                Continue
              </Button>
            </Box>
          </Paper>
        )}

        {/* Step 1: Connect Email */}
        {activeStep === 1 && (
          <Paper
            sx={{
              p: 4,
              bgcolor: '#ffffff',
              border: '1px solid rgba(255,255,255,0.08)',
              textAlign: 'center',
            }}
          >
            <Mail size={48} color="#4f7df9" style={{ marginBottom: 16 }} />
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              Connect Your Email
            </Typography>
            <Typography variant="body2" sx={{ color: '#6b7280', mb: 4, maxWidth: 400, mx: 'auto' }}>
              Connect a Gmail or Outlook account to send investor outreach emails directly from
              VentureStrat.
            </Typography>

            <Stack direction="row" spacing={2} sx={{ justifyContent: 'center', mb: 3 }}>
              <Button
                variant="outlined"
                sx={{
                  borderColor: '#4285f4',
                  color: '#4285f4',
                  px: 3,
                  '&:hover': { borderColor: '#4285f4', bgcolor: 'rgba(66,133,244,0.08)' },
                }}
              >
                Connect Gmail
              </Button>
              <Button
                variant="outlined"
                sx={{
                  borderColor: '#0078d4',
                  color: '#0078d4',
                  px: 3,
                  '&:hover': { borderColor: '#0078d4', bgcolor: 'rgba(0,120,212,0.08)' },
                }}
              >
                Connect Outlook
              </Button>
            </Stack>

            <Divider sx={{ my: 3, borderColor: 'rgba(255,255,255,0.06)' }} />

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={handleBack} sx={{ color: '#6b7280' }}>
                Back
              </Button>
              <Button
                variant="text"
                onClick={handleNext}
                endIcon={<SkipForward size={16} />}
                sx={{ color: '#6b7280' }}
              >
                Skip for now
              </Button>
            </Box>
          </Paper>
        )}

        {/* Step 2: Select Plan */}
        {activeStep === 2 && (
          <Box>
            <Typography
              variant="h6"
              sx={{ fontWeight: 600, mb: 1, textAlign: 'center' }}
            >
              Choose Your Plan
            </Typography>
            <Typography
              variant="body2"
              sx={{ color: '#6b7280', mb: 4, textAlign: 'center' }}
            >
              Start free and upgrade anytime as your needs grow.
            </Typography>

            <PlanCards
              plans={plans}
              onSelect={handleSelectPlan}
            />

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
              <Button onClick={handleBack} sx={{ color: '#6b7280' }}>
                Back
              </Button>
              <Button
                variant="text"
                onClick={handleNext}
                endIcon={<SkipForward size={16} />}
                sx={{ color: '#6b7280' }}
              >
                Skip — use free plan
              </Button>
            </Box>
          </Box>
        )}

        {/* Step 3: Welcome */}
        {activeStep === 3 && (
          <Paper
            sx={{
              p: 5,
              bgcolor: '#ffffff',
              border: '1px solid rgba(255,255,255,0.08)',
              textAlign: 'center',
            }}
          >
            <Rocket size={56} color="#4f7df9" style={{ marginBottom: 16 }} />
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
              You're all set!
            </Typography>
            <Typography
              variant="body1"
              sx={{ color: '#6b7280', mb: 4, maxWidth: 400, mx: 'auto' }}
            >
              Your workspace is ready. Start exploring investors, setting up outreach
              campaigns, and building your pipeline.
            </Typography>

            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
              Quick Actions
            </Typography>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2}
              sx={{ justifyContent: 'center', mb: 4 }}
            >
              <Button
                variant="outlined"
                onClick={() => navigate('/investor')}
                sx={{ borderColor: '#4f7df9', color: '#4f7df9' }}
              >
                Browse Investors
              </Button>
              <Button
                variant="outlined"
                onClick={() => navigate('/outreach')}
                sx={{ borderColor: '#66bb6a', color: '#66bb6a' }}
              >
                Set Up Outreach
              </Button>
              <Button
                variant="outlined"
                onClick={() => navigate('/crm')}
                sx={{ borderColor: '#ff9800', color: '#ff9800' }}
              >
                Manage Pipeline
              </Button>
            </Stack>

            <Button
              variant="contained"
              size="large"
              onClick={handleComplete}
              endIcon={<ArrowRight size={18} />}
              sx={{
                bgcolor: '#4f7df9',
                color: '#f9fafb',
                fontWeight: 600,
                px: 5,
                '&:hover': { bgcolor: '#4f7df9', opacity: 0.9 },
              }}
            >
              Go to Dashboard
            </Button>
          </Paper>
        )}
      </Box>
    </Box>
  );
};

export default OnboardingPage;
