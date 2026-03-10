import React, { useState, useRef } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Avatar from '@mui/material/Avatar';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { Country } from 'country-state-city';
import { useAuth } from '../../../auth/AuthProvider';
import {
  useConnectedAccounts,
  useGoogleConnect,
  useMicrosoftConnect,
} from '../../outreach/hooks/useEmailAccounts';

// ---------------------------------------------------------------------------
// Provider icons (inline SVG)
// ---------------------------------------------------------------------------

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" fill="#34A853" />
      <path d="M5.84 14.09A6.97 6.97 0 0 1 5.47 12c0-.72.13-1.43.37-2.09V7.07H2.18A11.96 11.96 0 0 0 .96 12c0 1.94.46 3.77 1.22 5.33l3.66-3.24Z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 1.99 14.97.96 12 .96 7.7.96 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53Z" fill="#EA4335" />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="10" height="10" fill="#F25022" />
      <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
      <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
      <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Dropdown options
// ---------------------------------------------------------------------------

const INDUSTRIES = [
  'Technology',
  'Healthcare',
  'Finance',
  'E-Commerce',
  'SaaS',
  'Research & Development',
  'Education',
  'Real Estate',
  'Energy & CleanTech',
  'Consumer Goods',
  'Media & Entertainment',
  'Logistics & Supply Chain',
  'Agriculture & FoodTech',
  'Cybersecurity',
  'AI & Machine Learning',
  'Biotech & Pharma',
  'Other',
];

const INVESTMENT_STAGES = [
  'Pre-Seed',
  'Seed',
  'Early Stage Venture',
  'Series A',
  'Series B',
  'Growth',
  'Late Stage',
  'Pre-IPO',
  'Bootstrapped',
];

const REGION_OPTIONS = [
  'Worldwide',
  'North America',
  'Europe',
  'Asia Pacific',
  'Middle East & Africa',
  'Latin America',
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const SettingsPage: React.FC = () => {
  const { user } = useAuth();

  // Profile fields
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState(user?.username ?? '');
  const [email, setEmail] = useState(`${user?.username ?? 'user'}@venturestrat.io`);
  const [password] = useState('••••••••••');
  const [companyName, setCompanyName] = useState('');
  const [companyWebsite, setCompanyWebsite] = useState('');
  const [country, setCountry] = useState('');
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fundraising context fields
  const [industry, setIndustry] = useState('');
  const [investmentStage, setInvestmentStage] = useState('');
  const [bizCountry, setBizCountry] = useState('');
  const [bizRegion, setBizRegion] = useState('');
  const [traction, setTraction] = useState('');

  // Integration
  const userId = user?.id ?? user?.username ?? 'anonymous';
  const { data: accounts = [] } = useConnectedAccounts(userId);
  const googleConnect = useGoogleConnect(userId);
  const microsoftConnect = useMicrosoftConnect(userId);

  const googleAccount = accounts.find((a) => a.provider === 'gmail');
  const microsoftAccount = accounts.find((a) => a.provider === 'microsoft');

  // Snackbar
  const [snackOpen, setSnackOpen] = useState(false);

  const countries = Country.getAllCountries();

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setLogoPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handleSave = () => {
    setSnackOpen(true);
  };

  // Shared style for Paper sections
  const sectionSx = {
    p: 3,
    mb: 3,
    bgcolor: '#ffffff',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 2,
  };

  return (
    <Box sx={{ maxWidth: 960, mx: 'auto', p: { xs: 2, md: 4 } }}>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
        Settings
      </Typography>
      <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
        Manage your profile, integrations, and fundraising preferences.
      </Typography>

      {/* ================================================================= */}
      {/* PROFILE SECTION                                                   */}
      {/* ================================================================= */}
      <Paper sx={sectionSx}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
          Profile
        </Typography>

        <Grid container spacing={2.5}>
          {/* Row 1: First Name, Last Name, Email */}
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              label="First Name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              placeholder="John"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              label="Last Name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              placeholder="Doe"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              label="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              disabled
              helperText="Email cannot be changed here."
            />
          </Grid>

          {/* Row 2: Password, Company Name, Company Website */}
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              label="Password"
              value={password}
              fullWidth
              variant="outlined"
              size="small"
              type="password"
              disabled
              helperText="Change via account security."
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              label="Company Name"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              placeholder="Acme Corp"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              label="Company Website"
              value={companyWebsite}
              onChange={(e) => setCompanyWebsite(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              placeholder="https://acme.com"
            />
          </Grid>

          {/* Row 3: Company Logo, Country */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="body2" sx={{ color: '#6b7280', mb: 1 }}>
              Company Logo
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {logoPreview ? (
                <Avatar
                  src={logoPreview}
                  variant="rounded"
                  sx={{ width: 48, height: 48, border: '1px solid rgba(255,255,255,0.12)' }}
                />
              ) : (
                <Avatar
                  variant="rounded"
                  sx={{
                    width: 48,
                    height: 48,
                    bgcolor: 'rgba(255,255,255,0.06)',
                    color: '#556677',
                    fontSize: '0.75rem',
                  }}
                >
                  Logo
                </Avatar>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                hidden
                onChange={handleLogoUpload}
              />
              <Button
                variant="outlined"
                size="small"
                onClick={() => fileInputRef.current?.click()}
                sx={{ borderColor: 'rgba(255,255,255,0.2)', color: '#6b7280', textTransform: 'none' }}
              >
                Upload Logo
              </Button>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              label="Country"
              select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              SelectProps={{ MenuProps: { PaperProps: { sx: { maxHeight: 300 } } } }}
            >
              <MenuItem value="">
                <em>Select country</em>
              </MenuItem>
              {countries.map((c) => (
                <MenuItem key={c.isoCode} value={c.isoCode}>
                  {c.flag} {c.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3 }}>
          <Button
            variant="contained"
            onClick={handleSave}
            sx={{
              bgcolor: '#4f7df9',
              color: '#f9fafb',
              fontWeight: 600,
              textTransform: 'none',
              '&:hover': { bgcolor: '#39b0e6' },
            }}
          >
            Save Changes
          </Button>
        </Box>
      </Paper>

      {/* ================================================================= */}
      {/* INTEGRATION SECTION                                               */}
      {/* ================================================================= */}
      <Paper sx={sectionSx}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
          Integration
        </Typography>
        <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
          Configure Google or Microsoft connections for email delivery and webhook support.
          You can only connect one account (Google or Microsoft). Disconnect the current account to connect the other.
        </Typography>

        {/* Google row */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 2,
            mb: 1.5,
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 1.5,
            bgcolor: 'rgba(255,255,255,0.02)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <GoogleIcon />
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Connect your Google Account
              </Typography>
              {googleAccount && (
                <Typography variant="caption" sx={{ color: '#6b7280' }}>
                  {googleAccount.email}
                </Typography>
              )}
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Chip
              label={googleAccount ? 'Connected' : 'Disconnected'}
              size="small"
              color={googleAccount ? 'success' : 'default'}
              variant="outlined"
            />
            <Button
              variant="outlined"
              size="small"
              onClick={() => googleConnect.mutate()}
              disabled={googleConnect.isPending}
              sx={{
                borderColor: '#4285f4',
                color: '#4285f4',
                textTransform: 'none',
                fontWeight: 500,
                minWidth: 100,
                '&:hover': { borderColor: '#4285f4', bgcolor: 'rgba(66,133,244,0.08)' },
              }}
            >
              {googleConnect.isPending
                ? 'Redirecting...'
                : googleAccount
                  ? 'Reconnect'
                  : 'Connect'}
            </Button>
          </Box>
        </Box>

        {/* Microsoft row */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 2,
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 1.5,
            bgcolor: 'rgba(255,255,255,0.02)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <MicrosoftIcon />
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Connect your Microsoft Account
              </Typography>
              {microsoftAccount && (
                <Typography variant="caption" sx={{ color: '#6b7280' }}>
                  {microsoftAccount.email}
                </Typography>
              )}
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Chip
              label={microsoftAccount ? 'Connected' : 'Disconnected'}
              size="small"
              color={microsoftAccount ? 'success' : 'default'}
              variant="outlined"
            />
            <Button
              variant="outlined"
              size="small"
              onClick={() => microsoftConnect.mutate()}
              disabled={microsoftConnect.isPending}
              sx={{
                borderColor: '#0078d4',
                color: '#0078d4',
                textTransform: 'none',
                fontWeight: 500,
                minWidth: 100,
                '&:hover': { borderColor: '#0078d4', bgcolor: 'rgba(0,120,212,0.08)' },
              }}
            >
              {microsoftConnect.isPending
                ? 'Redirecting...'
                : microsoftAccount
                  ? 'Reconnect'
                  : 'Connect'}
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* ================================================================= */}
      {/* FUNDRAISING CONTEXT SECTION                                       */}
      {/* ================================================================= */}
      <Paper sx={sectionSx}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
          Fundraising
        </Typography>
        <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
          Tell us about your business so we can tailor investor recommendations and outreach templates.
        </Typography>

        <Grid container spacing={2.5}>
          <Grid size={12}>
            <TextField
              label="What industry or sector best describes your business?"
              select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
            >
              <MenuItem value="">
                <em>Select industry</em>
              </MenuItem>
              {INDUSTRIES.map((ind) => (
                <MenuItem key={ind} value={ind}>
                  {ind}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={12}>
            <TextField
              label="Which investment stage best defines your business?"
              select
              value={investmentStage}
              onChange={(e) => setInvestmentStage(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
            >
              <MenuItem value="">
                <em>Select stage</em>
              </MenuItem>
              {INVESTMENT_STAGES.map((stage) => (
                <MenuItem key={stage} value={stage}>
                  {stage}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={12}>
            <Typography variant="body2" sx={{ color: '#6b7280', mb: 1 }}>
              Where is your business incorporated and where do you operate?
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Country"
                  select
                  value={bizCountry}
                  onChange={(e) => setBizCountry(e.target.value)}
                  fullWidth
                  variant="outlined"
                  size="small"
                  SelectProps={{ MenuProps: { PaperProps: { sx: { maxHeight: 300 } } } }}
                >
                  <MenuItem value="">
                    <em>Select country</em>
                  </MenuItem>
                  {countries.map((c) => (
                    <MenuItem key={c.isoCode} value={c.isoCode}>
                      {c.flag} {c.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Region / Market"
                  select
                  value={bizRegion}
                  onChange={(e) => setBizRegion(e.target.value)}
                  fullWidth
                  variant="outlined"
                  size="small"
                >
                  <MenuItem value="">
                    <em>Select region</em>
                  </MenuItem>
                  {REGION_OPTIONS.map((r) => (
                    <MenuItem key={r} value={r}>
                      {r}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
            </Grid>
          </Grid>

          <Grid size={12}>
            <TextField
              label="What is your current annual revenue or key traction metric?"
              value={traction}
              onChange={(e) => setTraction(e.target.value)}
              fullWidth
              variant="outlined"
              size="small"
              placeholder="e.g. $500K ARR, 10K MAU, $2M GMV"
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 3, borderColor: 'rgba(255,255,255,0.06)' }} />

        <Button
          variant="contained"
          onClick={handleSave}
          sx={{
            bgcolor: '#4f7df9',
            color: '#f9fafb',
            fontWeight: 600,
            textTransform: 'none',
            '&:hover': { bgcolor: '#39b0e6' },
          }}
        >
          Save Changes
        </Button>
      </Paper>

      {/* Save confirmation */}
      <Snackbar
        open={snackOpen}
        autoHideDuration={3000}
        onClose={() => setSnackOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity="success"
          onClose={() => setSnackOpen(false)}
          variant="filled"
          sx={{ width: '100%' }}
        >
          Settings saved successfully.
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SettingsPage;
