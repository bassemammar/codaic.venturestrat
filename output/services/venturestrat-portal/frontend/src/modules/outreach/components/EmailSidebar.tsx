/**
 * EmailSidebar — vertical sidebar with status tabs and message list
 *
 * Tabs: Drafts, Sent, Inbox, Scheduled, All
 * Each tab filters messages by status.
 */

import React, { useState, useMemo, useCallback } from 'react';
import Box from '@mui/material/Box';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Badge from '@mui/material/Badge';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';
import { Search, Reply as ReplyIcon } from '@mui/icons-material';
import { format, isToday, isYesterday } from 'date-fns';
import type { Message } from '@outr/types/message.types';

export interface EmailSidebarProps {
  messages: Message[];
  selectedId?: string | null;
  onSelect: (message: Message) => void;
  isLoading?: boolean;
}

type TabKey = 'draft' | 'sent' | 'received' | 'scheduled' | 'all';

interface TabDef {
  key: TabKey;
  label: string;
  filter: (m: Message) => boolean;
}

const TABS: TabDef[] = [
  { key: 'draft', label: 'Drafts', filter: (m) => m.status === 'draft' },
  { key: 'sent', label: 'Sent', filter: (m) => m.status === 'sent' },
  { key: 'received', label: 'Inbox', filter: (m) => m.status === 'received' },
  { key: 'scheduled', label: 'Scheduled', filter: (m) => m.status === 'scheduled' },
  { key: 'all', label: 'All', filter: () => true },
];

const statusBorderColor: Record<string, string> = {
  draft: '#78909c',
  sent: '#4f7df9',
  received: '#66bb6a',
  scheduled: '#ff9800',
  failed: '#f44336',
  cancelled: '#9e9e9e',
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  if (isToday(d)) return format(d, 'h:mm a');
  if (isYesterday(d)) return 'Yesterday';
  return format(d, 'MMM d');
}

export const EmailSidebar: React.FC<EmailSidebarProps> = ({
  messages,
  selectedId,
  onSelect,
  isLoading = false,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('draft');
  const [search, setSearch] = useState('');

  const tabCounts = useMemo(() => {
    const counts: Record<TabKey, number> = { draft: 0, sent: 0, received: 0, scheduled: 0, all: 0 };
    for (const msg of messages) {
      counts.all++;
      if (msg.status === 'draft') counts.draft++;
      else if (msg.status === 'sent') counts.sent++;
      else if (msg.status === 'received') counts.received++;
      else if (msg.status === 'scheduled') counts.scheduled++;
    }
    return counts;
  }, [messages]);

  // Build a map of message id → reply count so we can show thread indicators
  const replyCountMap = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const msg of messages) {
      if (msg.previous_message_id) {
        counts[msg.previous_message_id] = (counts[msg.previous_message_id] || 0) + 1;
      }
    }
    return counts;
  }, [messages]);

  const filteredMessages = useMemo(() => {
    const tabDef = TABS.find((t) => t.key === activeTab) || TABS[4];
    let filtered = messages.filter(tabDef.filter);

    if (search.trim()) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (m) =>
          m.subject?.toLowerCase().includes(q) ||
          m.from_address?.toLowerCase().includes(q) ||
          formatAddressesForSearch(m.to_addresses).includes(q),
      );
    }

    // Sort by date descending
    return filtered.sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
  }, [messages, activeTab, search]);

  const handleTabChange = useCallback((_: React.SyntheticEvent, val: number) => {
    setActiveTab(TABS[val].key);
  }, []);

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid',
        borderColor: 'divider',
        bgcolor: '#ffffff',
      }}
    >
      {/* Tabs */}
      <Tabs
        value={TABS.findIndex((t) => t.key === activeTab)}
        onChange={handleTabChange}
        variant="scrollable"
        scrollButtons="auto"
        sx={{
          minHeight: 40,
          borderBottom: '1px solid',
          borderColor: 'divider',
          '& .MuiTab-root': {
            minHeight: 40,
            textTransform: 'none',
            fontSize: '0.75rem',
            px: 1.5,
            minWidth: 0,
          },
        }}
      >
        {TABS.map((tab) => (
          <Tab
            key={tab.key}
            label={
              <Badge
                badgeContent={tabCounts[tab.key]}
                color="primary"
                max={99}
                sx={{
                  '& .MuiBadge-badge': {
                    fontSize: '0.6rem',
                    minWidth: 16,
                    height: 16,
                  },
                }}
              >
                <Box sx={{ pr: tabCounts[tab.key] > 0 ? 1.5 : 0 }}>
                  {tab.label}
                </Box>
              </Badge>
            }
          />
        ))}
      </Tabs>

      {/* Search */}
      <Box sx={{ p: 1 }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Search messages..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" sx={{ color: 'text.disabled' }} />
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiInputBase-root': { fontSize: '0.8rem' },
            '& .MuiOutlinedInput-root': {
              bgcolor: 'rgba(255,255,255,0.03)',
            },
          }}
        />
      </Box>

      {/* Message List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {isLoading ? (
          <Box sx={{ p: 1 }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton
                key={i}
                variant="rectangular"
                height={64}
                sx={{ mb: 0.5, borderRadius: 1 }}
              />
            ))}
          </Box>
        ) : filteredMessages.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.disabled">
              No messages
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {filteredMessages.map((msg) => (
              <ListItemButton
                key={msg.id}
                selected={msg.id === selectedId}
                onClick={() => onSelect(msg)}
                sx={{
                  py: 1,
                  px: 1.5,
                  borderLeft: '3px solid',
                  borderLeftColor: statusBorderColor[msg.status] || '#78909c',
                  '&.Mui-selected': {
                    bgcolor: 'rgba(79,195,247,0.08)',
                  },
                  '&:hover': {
                    bgcolor: 'rgba(79,195,247,0.04)',
                  },
                }}
              >
                <Box sx={{ width: '100%', overflow: 'hidden' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.25 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 600,
                        fontSize: '0.8rem',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: 160,
                      }}
                    >
                      {msg.status === 'received'
                        ? msg.from_address || '(unknown)'
                        : formatAddressesShort(msg.to_addresses) || '(no recipient)'}
                    </Typography>
                    <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.65rem', flexShrink: 0, ml: 0.5 }}>
                      {formatDate(msg.updated_at)}
                    </Typography>
                  </Box>
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: '0.75rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      color: 'text.secondary',
                    }}
                  >
                    {msg.subject || '(no subject)'}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5, gap: 0.5 }}>
                    <Chip
                      label={msg.status}
                      size="small"
                      sx={{
                        height: 16,
                        fontSize: '0.6rem',
                        bgcolor: `${statusBorderColor[msg.status] || '#78909c'}20`,
                        color: statusBorderColor[msg.status] || '#78909c',
                        fontWeight: 600,
                      }}
                    />
                    {msg.scheduled_for && msg.status === 'scheduled' && (
                      <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.6rem' }}>
                        {format(new Date(msg.scheduled_for), 'MMM d, h:mm a')}
                      </Typography>
                    )}
                    {/* Reply count indicator */}
                    {replyCountMap[msg.id] ? (
                      <Tooltip title={`${replyCountMap[msg.id]} repl${replyCountMap[msg.id] === 1 ? 'y' : 'ies'}`}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, ml: 'auto' }}>
                          <ReplyIcon sx={{ fontSize: 11, color: '#6b7280' }} />
                          <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#6b7280' }}>
                            {replyCountMap[msg.id]}
                          </Typography>
                        </Box>
                      </Tooltip>
                    ) : null}
                  </Box>
                </Box>
              </ListItemButton>
            ))}
          </List>
        )}
      </Box>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatAddressesShort(val: unknown): string {
  const arr = parseAddrs(val);
  if (arr.length === 0) return '';
  if (arr.length === 1) return arr[0];
  return `${arr[0]} +${arr.length - 1}`;
}

function formatAddressesForSearch(val: unknown): string {
  return parseAddrs(val).join(' ').toLowerCase();
}

function parseAddrs(val: unknown): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val as string[];
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) return parsed;
    } catch {
      return val.split(',').map((s) => s.trim()).filter(Boolean);
    }
  }
  return [];
}

export default EmailSidebar;
