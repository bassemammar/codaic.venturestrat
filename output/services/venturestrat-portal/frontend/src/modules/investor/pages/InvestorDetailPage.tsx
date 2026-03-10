import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Avatar from '@mui/material/Avatar';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import Snackbar from '@mui/material/Snackbar';
import CircularProgress from '@mui/material/CircularProgress';
import {
  ArrowLeft,
  MapPin,
  Globe,
  Phone,
  Mail,
  Lock,
  CheckCircle,
  Linkedin,
  Twitter,
} from 'lucide-react';
import { useInvestorDetail } from '../hooks/useInvestorDetail';
import { useSubscriptionStatus } from '../hooks/useSubscriptionStatus';
import { useAuth } from '../../../auth/AuthProvider';
import { crmApi } from '@modules/crm/api/crmApi';
import { useQuery } from '@tanstack/react-query';

function parseJsonArray(value: unknown): string[] {
  if (Array.isArray(value)) return value;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) return parsed;
    } catch {
      // not JSON
    }
  }
  return [];
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

const AVATAR_COLORS = [
  '#1976d2', '#388e3c', '#7b1fa2', '#c62828',
  '#00838f', '#4527a0', '#ef6c00', '#2e7d32',
  '#ad1457', '#0277bd', '#6a1b9a', '#558b2f',
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function maskEmail(email: string): string {
  const [local, domain] = email.split('@');
  if (!domain) return email;
  const visible = local.slice(0, 4);
  return `${visible}${'*'.repeat(Math.max(local.length - 4, 2))}@${domain}`;
}

const SectionCard: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <Paper
    variant="outlined"
    sx={{
      borderColor: '#e5e7eb',
      borderRadius: 2,
      p: 2.5,
      height: '100%',
    }}
  >
    <Typography
      variant="subtitle1"
      sx={{ fontWeight: 700, color: '#1a1a1a', mb: 1.5 }}
    >
      {title}
    </Typography>
    {children}
  </Paper>
);

const InvestorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data, isLoading, isError, error } = useInvestorDetail(id);
  const { data: subStatus } = useSubscriptionStatus();

  const [adding, setAdding] = useState(false);
  const [shortlisted, setShortlisted] = useState(false);
  const [snackOpen, setSnackOpen] = useState(false);
  const [snackMsg, setSnackMsg] = useState('');

  const { data: pipelineStages } = useQuery({
    queryKey: ['crm', 'pipeline-stages-for-detail'],
    queryFn: () => crmApi.getPipelineStages(),
    staleTime: 30 * 60 * 1000,
  });

  const firstStageId = React.useMemo(() => {
    if (!pipelineStages || pipelineStages.length === 0) return null;
    const sorted = [...pipelineStages].sort((a, b) => a.sequence - b.sequence);
    return sorted[0]?.id ?? null;
  }, [pipelineStages]);

  if (isLoading) {
    return (
      <Box sx={{ px: 3, py: 2, maxWidth: 1200, mx: 'auto' }}>
        <Skeleton variant="rounded" height={40} width={120} sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={160} sx={{ borderRadius: 2, mb: 2 }} />
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}><Skeleton variant="rounded" height={180} sx={{ borderRadius: 2 }} /></Grid>
          <Grid size={{ xs: 12, md: 4 }}><Skeleton variant="rounded" height={180} sx={{ borderRadius: 2 }} /></Grid>
          <Grid size={{ xs: 12, md: 4 }}><Skeleton variant="rounded" height={180} sx={{ borderRadius: 2 }} /></Grid>
        </Grid>
      </Box>
    );
  }

  if (isError || !data) {
    return (
      <Box sx={{ px: 3, py: 2, maxWidth: 1200, mx: 'auto' }}>
        <Button
          startIcon={<ArrowLeft size={16} />}
          onClick={() => navigate('/investor/search')}
          sx={{ color: '#6b7280', textTransform: 'none', mb: 2 }}
        >
          Back to Directory
        </Button>
        <Alert severity="error">
          {(error as Error)?.message ?? 'Failed to load investor details.'}
        </Alert>
      </Box>
    );
  }

  const { investor, emails, markets, pastInvestments } = data;
  const stages = parseJsonArray(investor.stages);
  const types = parseJsonArray(investor.investor_types);
  const location = [investor.city, investor.state, investor.country]
    .filter(Boolean)
    .join(', ');
  const hasSubscription = subStatus?.hasActiveSubscription ?? false;
  const planCode = subStatus?.planCode ?? null;
  const isPaidPlan =
    hasSubscription &&
    planCode != null &&
    ['starter', 'pro', 'scale'].includes(planCode.toLowerCase());
  const canSeeFullContact = isPaidPlan;

  const linkedinUrl = investor.social_links?.linkedin ?? investor.social_links?.Linkedin ?? null;
  const twitterUrl = investor.social_links?.twitter ?? investor.social_links?.Twitter ?? investor.social_links?.x ?? null;

  async function handleShortlist() {
    if (shortlisted || adding) return;
    setAdding(true);
    try {
      await crmApi.createShortlist({
        user_id: user?.id ?? '',
        investor_id: investor.id,
        stage_id: firstStageId ?? undefined,
        status: 'target',
        notes: '',
        added_at: new Date().toISOString(),
      });
      setShortlisted(true);
      setSnackMsg(`${investor.name} added to pipeline`);
      setSnackOpen(true);
    } catch {
      setSnackMsg('Failed to add to pipeline.');
      setSnackOpen(true);
    } finally {
      setAdding(false);
    }
  }

  return (
    <Box sx={{ px: 3, py: 2, maxWidth: 1200, mx: 'auto' }}>
      {/* Breadcrumb */}
      <Breadcrumbs sx={{ mb: 1, fontSize: 13 }}>
        <Link
          underline="hover"
          color="#6b7280"
          sx={{ cursor: 'pointer', fontSize: 13 }}
          onClick={() => navigate('/')}
        >
          Home
        </Link>
        <Link
          underline="hover"
          color="#6b7280"
          sx={{ cursor: 'pointer', fontSize: 13 }}
          onClick={() => {}}
        >
          Fundraising
        </Link>
        <Link
          underline="hover"
          color="#6b7280"
          sx={{ cursor: 'pointer', fontSize: 13 }}
          onClick={() => navigate('/investor/search')}
        >
          Investors
        </Link>
        <Typography color="#374151" sx={{ fontSize: 13 }}>
          Investor Details
        </Typography>
      </Breadcrumbs>

      {/* Back link */}
      <Button
        startIcon={<ArrowLeft size={16} />}
        onClick={() => navigate('/investor/search')}
        sx={{ color: '#374151', textTransform: 'none', mb: 2, fontWeight: 600, fontSize: 15, pl: 0 }}
      >
        Back to Directory
      </Button>

      {/* Header card */}
      <Paper
        variant="outlined"
        sx={{
          borderColor: '#e5e7eb',
          borderRadius: 2,
          p: 3,
          mb: 2,
          background: 'linear-gradient(135deg, #f0f4ff 0%, #f9fafb 100%)',
        }}
      >
        <Box sx={{ display: 'flex', gap: 2.5, alignItems: 'flex-start' }}>
          <Avatar
            src={investor.avatar ?? undefined}
            sx={{
              width: 80,
              height: 80,
              bgcolor: getAvatarColor(investor.name),
              color: '#ffffff',
              fontSize: 28,
              fontWeight: 700,
              flexShrink: 0,
              border: '3px solid',
              borderColor: `${getAvatarColor(investor.name)}40`,
            }}
          >
            {getInitials(investor.name)}
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
              <Typography variant="h5" sx={{ fontWeight: 700, color: '#1a1a1a' }}>
                {investor.name}
              </Typography>
              <Chip
                icon={<CheckCircle size={12} />}
                label="Verified"
                size="small"
                color="success"
                sx={{ height: 22, fontSize: 11, fontWeight: 600, '& .MuiChip-icon': { fontSize: 12, ml: 0.5 }, '& .MuiChip-label': { px: 0.75 } }}
              />
            </Box>
            {(investor.title || investor.company_name) && (
              <Typography variant="body1" sx={{ color: '#6b7280' }}>
                {investor.title}
                {investor.title && investor.company_name ? ' at ' : ''}
                {investor.company_name}
              </Typography>
            )}
            {types.length > 0 && (
              <Stack direction="row" spacing={0.5} sx={{ mt: 1, flexWrap: 'wrap', gap: 0.5 }}>
                {types.map((t) => (
                  <Chip
                    key={t}
                    label={t}
                    size="small"
                    variant="outlined"
                    sx={{ height: 24, fontSize: 12, color: '#555', borderColor: '#ccc' }}
                  />
                ))}
              </Stack>
            )}
          </Box>
          <Box sx={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
            <Button
              variant="contained"
              size="small"
              onClick={handleShortlist}
              disabled={shortlisted || adding}
              sx={{
                textTransform: 'none',
                bgcolor: shortlisted ? '#4caf50' : '#1976d2',
                fontWeight: 600,
                px: 2.5,
                '&:hover': { bgcolor: shortlisted ? '#4caf50' : '#1565c0' },
                '&.Mui-disabled': { bgcolor: shortlisted ? '#4caf50' : undefined, color: shortlisted ? '#fff' : undefined },
              }}
            >
              {adding ? <CircularProgress size={16} sx={{ color: '#fff' }} /> : shortlisted ? 'Shortlisted' : 'Shortlist +'}
            </Button>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {linkedinUrl && (
                <Box
                  component="a"
                  href={typeof linkedinUrl === 'string' ? linkedinUrl : '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ color: '#0077b5', '&:hover': { opacity: 0.8 } }}
                >
                  <Linkedin size={24} />
                </Box>
              )}
              {twitterUrl && (
                <Box
                  component="a"
                  href={typeof twitterUrl === 'string' ? twitterUrl : '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ color: '#1a1a1a', '&:hover': { opacity: 0.8 } }}
                >
                  <Twitter size={24} />
                </Box>
              )}
            </Box>
          </Box>
        </Box>
      </Paper>

      {/* Info cards grid */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        {/* Contact Info */}
        <Grid size={{ xs: 12, md: 4 }}>
          <SectionCard title="Contact Info">
            {!canSeeFullContact && !hasSubscription ? (
              <Box sx={{ textAlign: 'center', py: 2 }}>
                <Lock size={32} color="#9ca3af" />
                <Typography variant="body2" sx={{ color: '#6b7280', mt: 1, mb: 1.5 }}>
                  Upgrade to view contact info
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/billing/subscription')}
                  sx={{ textTransform: 'none', fontWeight: 600 }}
                >
                  View Plans
                </Button>
              </Box>
            ) : (
              <Stack spacing={1.5}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Phone size={16} color="#6b7280" />
                  <Typography variant="body2" sx={{ color: '#374151' }}>
                    {investor.phone || '\u2014'}
                  </Typography>
                </Box>
                {location && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <MapPin size={16} color="#6b7280" />
                    <Typography variant="body2" sx={{ color: '#374151' }}>
                      {location}
                    </Typography>
                  </Box>
                )}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Globe size={16} color="#6b7280" />
                  <Typography variant="body2" sx={{ color: '#374151' }}>
                    {investor.website || '\u2014'}
                  </Typography>
                </Box>
                {emails.length > 0 && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Mail size={16} color="#6b7280" />
                    <Typography variant="body2" sx={{ color: '#374151' }}>
                      {canSeeFullContact ? emails[0].email : maskEmail(emails[0].email)}
                    </Typography>
                  </Box>
                )}
              </Stack>
            )}
          </SectionCard>
        </Grid>

        {/* Investment Stages */}
        <Grid size={{ xs: 12, md: 4 }}>
          <SectionCard title="Investment Stages">
            {stages.length > 0 ? (
              <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                {stages.map((s) => (
                  <Chip
                    key={s}
                    label={s}
                    size="small"
                    variant="outlined"
                    sx={{ borderColor: '#93c5fd', color: '#2563eb', bgcolor: '#eff6ff' }}
                  />
                ))}
              </Stack>
            ) : (
              <Box sx={{ py: 2, textAlign: 'center', bgcolor: '#f9fafb', borderRadius: 1 }}>
                <Typography variant="body2" sx={{ color: '#9ca3af' }}>
                  No investment stages specified
                </Typography>
              </Box>
            )}

            {/* Markets sub-section */}
            {markets.length > 0 && (
              <Box sx={{ mt: 2.5 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#1a1a1a', mb: 1 }}>
                  Markets
                </Typography>
                <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                  {markets.map((m) => (
                    <Chip
                      key={m.id}
                      label={m.title}
                      size="small"
                      variant="outlined"
                      sx={{ borderColor: '#86efac', color: '#16a34a', bgcolor: '#f0fdf4' }}
                    />
                  ))}
                </Stack>
              </Box>
            )}
          </SectionCard>
        </Grid>

        {/* Social Links */}
        <Grid size={{ xs: 12, md: 4 }}>
          <SectionCard title="Social Links">
            {linkedinUrl || twitterUrl ? (
              <Stack spacing={1.5}>
                {twitterUrl && (
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Twitter size={18} color="#1a1a1a" />
                      <Typography variant="body2" sx={{ color: '#374151' }}>
                        Twitter
                      </Typography>
                    </Box>
                    <Typography sx={{ color: '#4f7df9', fontSize: 18, letterSpacing: 2 }}>
                      {'●●●●●'}
                    </Typography>
                  </Box>
                )}
                {linkedinUrl && (
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Linkedin size={18} color="#0077b5" />
                      <Typography variant="body2" sx={{ color: '#374151' }}>
                        Linkedin
                      </Typography>
                    </Box>
                    <Typography sx={{ color: '#4f7df9', fontSize: 18, letterSpacing: 2 }}>
                      {'●●●●●'}
                    </Typography>
                  </Box>
                )}
              </Stack>
            ) : (
              <Typography variant="body2" sx={{ color: '#9ca3af', py: 2, textAlign: 'center' }}>
                No social links available
              </Typography>
            )}
          </SectionCard>
        </Grid>
      </Grid>

      {/* Emails section */}
      {emails.length > 0 && (
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid size={{ xs: 12, md: 4 }}>
            <SectionCard title="Emails">
              <Stack spacing={1}>
                {emails.map((e) => (
                  <Box key={e.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Mail size={16} color="#6b7280" />
                    <Typography variant="body2" sx={{ color: '#374151' }}>
                      {canSeeFullContact ? e.email : maskEmail(e.email)}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </SectionCard>
          </Grid>
        </Grid>
      )}

      {/* Past Investments */}
      <Paper
        variant="outlined"
        sx={{ borderColor: '#e5e7eb', borderRadius: 2, p: 2.5 }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#1a1a1a', mb: 1.5 }}>
          Past Investments
        </Typography>
        {pastInvestments.length > 0 ? (
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            {pastInvestments.map((pi) => (
              <Chip
                key={pi.id}
                label={pi.title}
                size="small"
                variant="outlined"
                sx={{
                  borderColor: '#93c5fd',
                  color: '#2563eb',
                  bgcolor: '#eff6ff',
                  height: 28,
                  fontSize: 13,
                }}
              />
            ))}
          </Stack>
        ) : (
          <Box sx={{ py: 2, textAlign: 'center', bgcolor: '#f9fafb', borderRadius: 1 }}>
            <Typography variant="body2" sx={{ color: '#9ca3af' }}>
              No past investments listed
            </Typography>
          </Box>
        )}
      </Paper>

      <Snackbar
        open={snackOpen}
        autoHideDuration={2500}
        onClose={() => setSnackOpen(false)}
        message={snackMsg}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default InvestorDetailPage;
