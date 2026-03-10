import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '@mui/material/Card';
import Avatar from '@mui/material/Avatar';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Snackbar from '@mui/material/Snackbar';
import CircularProgress from '@mui/material/CircularProgress';
import { MapPin, Globe, CheckCircle } from 'lucide-react';
import type { Investor } from '@inve/types/investor.types';
import { crmApi } from '@modules/crm/api/crmApi';
import { useAuth } from '../../../auth/AuthProvider';
import SubscriptionLimitModal from './SubscriptionLimitModal';
import { useSubscriptionStatus } from '../hooks/useSubscriptionStatus';

interface InvestorCardProps {
  investor: Investor;
  hasSubscription?: boolean;
  shortlistedIds?: Set<string>;
  firstStageId?: string | null;
  onShortlisted?: (investorId: string) => void;
}

// Deterministic color from name hash
const AVATAR_COLORS = [
  '#1976d2', '#388e3c', '#7b1fa2', '#c62828',
  '#00838f', '#4527a0', '#ef6c00', '#2e7d32',
  '#ad1457', '#0277bd', '#6a1b9a', '#558b2f',
];

function getInitials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

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

function locationString(investor: Investor): string {
  const parts = [investor.state, investor.country].filter(Boolean);
  return parts.join(', ');
}

function formatWebsite(url: string | null): string | null {
  if (!url) return null;
  return url.replace(/^https?:\/\//, '').replace(/\/$/, '');
}

const InvestorCard: React.FC<InvestorCardProps> = ({
  investor,
  hasSubscription = false,
  shortlistedIds,
  firstStageId,
  onShortlisted,
}) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: subStatus } = useSubscriptionStatus();

  const stages = parseJsonArray(investor.stages);
  const types = parseJsonArray(investor.investor_types);
  const location = locationString(investor);
  const website = formatWebsite(investor.website);
  const primaryStage = stages.length > 0 ? stages[0] : null;

  const isAlreadyShortlisted = shortlistedIds?.has(investor.id) ?? false;

  const [adding, setAdding] = useState(false);
  const [addedLocally, setAddedLocally] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');
  const [limitModalOpen, setLimitModalOpen] = useState(false);

  const isShortlisted = isAlreadyShortlisted || addedLocally;

  async function handleShortlist(e: React.MouseEvent) {
    e.stopPropagation();
    e.preventDefault();

    if (isShortlisted || adding) return;

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
      setAddedLocally(true);
      setSnackbarMsg(`${investor.name} added to pipeline`);
      setSnackbarOpen(true);
      onShortlisted?.(investor.id);
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 403) {
        setLimitModalOpen(true);
      } else {
        setSnackbarMsg('Failed to add to pipeline. Please try again.');
        setSnackbarOpen(true);
      }
    } finally {
      setAdding(false);
    }
  }

  const avatarColor = getAvatarColor(investor.name);

  return (
    <>
      <Card
        sx={{
          bgcolor: '#ffffff',
          border: '1px solid #e0e0e0',
          borderRadius: 2,
          transition: 'box-shadow 0.2s',
          cursor: 'pointer',
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
          },
        }}
        onClick={() => navigate(`/investor/discover/${investor.id}`)}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            px: 2.5,
            py: 2,
            gap: 2.5,
            minHeight: 100,
          }}
        >
          {/* Section 1: Avatar */}
          <Avatar
            src={investor.avatar ?? undefined}
            sx={{
              width: 48,
              height: 48,
              bgcolor: avatarColor,
              color: '#ffffff',
              fontSize: 16,
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            {getInitials(investor.name)}
          </Avatar>

          {/* Section 2: Name + Verified + Title + Type Chips */}
          <Box sx={{ minWidth: 0, flex: '1 1 280px', maxWidth: 320 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
              <Typography
                variant="subtitle1"
                sx={{
                  fontWeight: 700,
                  color: '#1a1a1a',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  lineHeight: 1.4,
                }}
              >
                {investor.name}
              </Typography>
              <Chip
                icon={<CheckCircle size={12} />}
                label="Verified"
                size="small"
                color="success"
                sx={{
                  height: 22,
                  fontSize: 11,
                  fontWeight: 600,
                  flexShrink: 0,
                  '& .MuiChip-icon': {
                    fontSize: 12,
                    ml: 0.5,
                  },
                  '& .MuiChip-label': {
                    px: 0.75,
                  },
                }}
              />
            </Box>

            {(investor.title || investor.company_name) && (
              <Typography
                variant="body2"
                sx={{
                  color: '#666666',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  mb: 0.75,
                  lineHeight: 1.4,
                }}
              >
                {investor.title}
                {investor.title && investor.company_name ? ' at ' : ''}
                {investor.company_name}
              </Typography>
            )}

            {types.length > 0 && (
              <Stack
                direction="row"
                spacing={0.5}
                sx={{ flexWrap: 'wrap', gap: 0.5 }}
              >
                {types.slice(0, 3).map((t) => (
                  <Chip
                    key={t}
                    label={t}
                    size="small"
                    variant="outlined"
                    sx={{
                      height: 22,
                      fontSize: 11,
                      color: '#555555',
                      borderColor: '#cccccc',
                      '& .MuiChip-label': { px: 0.75 },
                    }}
                  />
                ))}
                {types.length > 3 && (
                  <Chip
                    label={`+${types.length - 3}`}
                    size="small"
                    variant="outlined"
                    sx={{
                      height: 22,
                      fontSize: 11,
                      color: '#999999',
                      borderColor: '#dddddd',
                      '& .MuiChip-label': { px: 0.75 },
                    }}
                  />
                )}
              </Stack>
            )}
          </Box>

          {/* Section 3: Location + Website */}
          <Box
            sx={{
              flex: '1 1 200px',
              maxWidth: 260,
              display: { xs: 'none', md: 'flex' },
              flexDirection: 'column',
              gap: 0.5,
            }}
          >
            {location && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                <MapPin size={14} color="#888888" />
                <Typography
                  variant="body2"
                  sx={{
                    color: '#555555',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {location}
                </Typography>
              </Box>
            )}
            {website && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                <Globe size={14} color="#888888" />
                <Typography
                  variant="body2"
                  sx={{
                    color: '#1976d2',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {website}
                </Typography>
              </Box>
            )}
          </Box>

          {/* Section 4: Investment Stage */}
          <Box
            sx={{
              flex: '0 0 auto',
              minWidth: 130,
              display: { xs: 'none', lg: 'block' },
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: '#999999',
                display: 'block',
                fontWeight: 600,
                fontSize: 11,
                mb: 0.25,
              }}
            >
              Investment Stage
            </Typography>
            <Typography
              variant="body2"
              sx={{
                color: primaryStage ? '#333333' : '#9ca3af',
                fontWeight: primaryStage ? 600 : 400,
              }}
            >
              {primaryStage ?? 'Not available'}
            </Typography>
          </Box>

          {/* Section 5: Action Buttons */}
          <Stack
            direction="row"
            spacing={1}
            sx={{ flexShrink: 0, ml: 'auto' }}
          >
            <Button
              variant="outlined"
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/investor/discover/${investor.id}`);
              }}
              sx={{
                textTransform: 'none',
                borderColor: '#cccccc',
                color: '#555555',
                fontWeight: 500,
                fontSize: 13,
                px: 2,
                whiteSpace: 'nowrap',
                '&:hover': {
                  borderColor: '#999999',
                  bgcolor: '#f5f5f5',
                },
              }}
            >
              View Profile
            </Button>
            <Button
              variant="contained"
              size="small"
              onClick={handleShortlist}
              disabled={isShortlisted || adding}
              sx={{
                textTransform: 'none',
                bgcolor: isShortlisted ? '#4caf50' : '#1976d2',
                fontWeight: 500,
                fontSize: 13,
                px: 2,
                whiteSpace: 'nowrap',
                '&:hover': {
                  bgcolor: isShortlisted ? '#4caf50' : '#1565c0',
                },
                '&.Mui-disabled': {
                  bgcolor: isShortlisted ? '#4caf50' : undefined,
                  color: isShortlisted ? '#ffffff' : undefined,
                },
              }}
            >
              {adding ? (
                <CircularProgress size={16} sx={{ color: '#ffffff' }} />
              ) : isShortlisted ? (
                'Shortlisted'
              ) : (
                'Shortlist +'
              )}
            </Button>
          </Stack>
        </Box>
      </Card>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={2500}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMsg}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />

      <SubscriptionLimitModal
        open={limitModalOpen}
        onClose={() => setLimitModalOpen(false)}
        limitType="shortlists_per_month"
        current={0}
        limit={0}
        planName={subStatus?.planName ?? 'Free'}
        planCode={subStatus?.planCode ?? null}
      />
    </>
  );
};

export default InvestorCard;
