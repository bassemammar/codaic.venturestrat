import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import type { UsageRecord } from '@bill/types/usage_record.types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UsageItem {
  label: string;
  current: number;
  limit: number;
}

interface UsageDashboardProps {
  usage: UsageRecord | null;
  limits: Record<string, any>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getBarColor(pct: number): string {
  if (pct >= 80) return '#ef5350';
  if (pct >= 50) return '#ffa726';
  return '#66bb6a';
}

function buildUsageItems(
  usage: UsageRecord | null,
  limits: Record<string, any>,
): UsageItem[] {
  if (!limits || Object.keys(limits).length === 0) return [];

  const mapping: Array<{
    limitKey: string;
    usageKey: keyof UsageRecord;
    label: string;
  }> = [
    { limitKey: 'ai_drafts_per_day', usageKey: 'ai_drafts_used', label: 'AI Drafts Today' },
    { limitKey: 'emails_per_month', usageKey: 'monthly_emails_sent', label: 'Emails This Month' },
    { limitKey: 'emails_per_day', usageKey: 'emails_sent', label: 'Emails Today' },
    { limitKey: 'contacts_limit', usageKey: 'monthly_investors_added', label: 'Contacts Added' },
    { limitKey: 'investors_per_month', usageKey: 'monthly_investors_added', label: 'Investors This Month' },
    { limitKey: 'investors_per_day', usageKey: 'investors_added', label: 'Investors Today' },
    { limitKey: 'templates_limit', usageKey: 'monthly_follow_ups_sent', label: 'Follow-ups This Month' },
    { limitKey: 'follow_ups_per_month', usageKey: 'monthly_follow_ups_sent', label: 'Follow-ups This Month' },
  ];

  const items: UsageItem[] = [];
  const seenLabels = new Set<string>();

  for (const m of mapping) {
    const limitVal = limits[m.limitKey];
    if (limitVal === undefined || limitVal === null) continue;
    if (seenLabels.has(m.label)) continue;
    seenLabels.add(m.label);

    const current = usage ? (usage[m.usageKey] as number) ?? 0 : 0;
    const limit = typeof limitVal === 'number' ? limitVal : parseInt(String(limitVal), 10) || 0;

    items.push({ label: m.label, current, limit });
  }

  return items;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const UsageDashboard: React.FC<UsageDashboardProps> = ({ usage, limits }) => {
  const items = buildUsageItems(usage, limits);

  if (items.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: '#6b7280' }}>
        No usage limits configured for your plan.
      </Typography>
    );
  }

  return (
    <Stack spacing={2}>
      {items.map((item) => {
        const pct = item.limit > 0
          ? Math.min(100, (item.current / item.limit) * 100)
          : 0;
        const isUnlimited = item.limit >= 999999;

        return (
          <Paper
            key={item.label}
            sx={{
              p: 2,
              bgcolor: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 1,
              }}
            >
              <Typography variant="body2" sx={{ color: '#374151', fontWeight: 500 }}>
                {item.label}
              </Typography>
              <Typography variant="body2" sx={{ color: '#6b7280' }}>
                {isUnlimited
                  ? `${item.current.toLocaleString()} / Unlimited`
                  : `${item.current.toLocaleString()} / ${item.limit.toLocaleString()}`}
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={isUnlimited ? 0 : pct}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: 'rgba(255,255,255,0.08)',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                  bgcolor: isUnlimited ? '#66bb6a' : getBarColor(pct),
                },
              }}
            />
          </Paper>
        );
      })}
    </Stack>
  );
};

export default UsageDashboard;
