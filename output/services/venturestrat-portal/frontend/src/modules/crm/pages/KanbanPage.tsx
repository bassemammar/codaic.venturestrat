import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Divider from '@mui/material/Divider';
import Chip from '@mui/material/Chip';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { useQuery } from '@tanstack/react-query';
import { X, Clock, MessageSquare, Phone, Mail, Calendar, FileText, Plus, Download } from 'lucide-react';
import { KanbanBoard } from '../components/KanbanBoard';
import { usePipelineStages } from '../hooks/usePipelineStages';
import { useUserShortlists } from '../hooks/useUserShortlists';
import { useShortlistActivities } from '../hooks/useShortlistActivities';
import { useUpdateShortlistStage } from '../hooks/useUpdateShortlistStage';
import { useCreateActivity } from '../hooks/useCreateActivity';
import { crmApi, type KanbanShortlist } from '../api/crmApi';
import type { Tag } from '@crm/types/tag.types';
import type { Activity } from '@crm/types/activity.types';

// ─── CSV Export ──────────────────────────────────────────────────────────────

/** Escape a value for CSV: wrap in quotes and double any internal quotes */
function escapeCsvValue(value: string | null | undefined): string {
  if (value == null) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function formatCsvDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

function exportShortlistsToCsv(shortlists: KanbanShortlist[]): void {
  const headers = ['Name', 'Company', 'Location', 'Stage', 'Status', 'Tags', 'Notes', 'Added Date'];

  const rows = shortlists.map((sl) => [
    escapeCsvValue(sl.investor_name || sl.investor_id),
    escapeCsvValue(sl.investor_company),
    escapeCsvValue(sl.investor_location),
    escapeCsvValue(sl.stage_name),
    escapeCsvValue(sl.status),
    escapeCsvValue(sl.tags.map((t) => t.name).join('; ')),
    escapeCsvValue(sl.notes),
    escapeCsvValue(formatCsvDate(sl.added_at)),
  ]);

  const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const today = new Date().toISOString().slice(0, 10);
  const filename = `venturestrat-pipeline-${today}.csv`;

  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ─────────────────────────────────────────────────────────────────────────────

const ACTIVITY_TYPES = [
  { value: 'note', label: 'Note', icon: FileText },
  { value: 'call', label: 'Call', icon: Phone },
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'meeting', label: 'Meeting', icon: Calendar },
  { value: 'message', label: 'Message', icon: MessageSquare },
];

const SIDEBAR_WIDTH = 400;

function getActivityIcon(type: string) {
  const found = ACTIVITY_TYPES.find((at) => at.value === type);
  const Icon = found?.icon || FileText;
  return <Icon size={14} />;
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

export const KanbanPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedShortlist, setSelectedShortlist] = useState<KanbanShortlist | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Activity form state
  const [newActivityType, setNewActivityType] = useState('note');
  const [newActivitySummary, setNewActivitySummary] = useState('');

  // Data hooks
  const { data: stages = [], isLoading: stagesLoading } = usePipelineStages();
  const { data: allTags = [] } = useQuery<Tag[]>({
    queryKey: ['crm', 'tags'],
    queryFn: () => crmApi.getTags(),
    staleTime: 30 * 60 * 1000,
  });
  const {
    data: shortlists = [],
    isLoading: shortlistsLoading,
  } = useUserShortlists(stages, allTags);
  const {
    data: activities = [],
    isLoading: activitiesLoading,
  } = useShortlistActivities(selectedShortlist?.id || null);

  // Mutations
  const updateStageMutation = useUpdateShortlistStage();
  const createActivityMutation = useCreateActivity();

  const handleCardClick = useCallback((shortlist: KanbanShortlist) => {
    setSelectedShortlist(shortlist);
    setDrawerOpen(true);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setDrawerOpen(false);
    setTimeout(() => setSelectedShortlist(null), 300);
  }, []);

  const handleDrop = useCallback(
    (shortlistId: string, newStageId: string) => {
      updateStageMutation.mutate({ shortlistId, stageId: newStageId });
    },
    [updateStageMutation],
  );

  const handleStageChange = useCallback(
    (newStageId: string) => {
      if (!selectedShortlist) return;
      updateStageMutation.mutate(
        { shortlistId: selectedShortlist.id, stageId: newStageId },
        {
          onSuccess: () => {
            setSelectedShortlist((prev) =>
              prev ? { ...prev, stage_id: newStageId } : null,
            );
          },
        },
      );
    },
    [selectedShortlist, updateStageMutation],
  );

  const handleAddActivity = useCallback(() => {
    if (!selectedShortlist || !newActivitySummary.trim()) return;
    createActivityMutation.mutate(
      {
        shortlist_id: selectedShortlist.id,
        activity_type: newActivityType,
        summary: newActivitySummary.trim(),
        date: new Date().toISOString(),
        user_id: selectedShortlist.user_id,
      },
      {
        onSuccess: () => {
          setNewActivitySummary('');
          setNewActivityType('note');
        },
      },
    );
  }, [selectedShortlist, newActivityType, newActivitySummary, createActivityMutation]);

  const handleExportCsv = useCallback(() => {
    if (shortlists.length === 0) return;
    setExporting(true);
    setTimeout(() => {
      try {
        exportShortlistsToCsv(shortlists);
      } finally {
        setExporting(false);
      }
    }, 50);
  }, [shortlists]);

  const isLoading = stagesLoading || shortlistsLoading;

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Page header */}
      <Box sx={{ px: 3, py: 2 }}>
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
          <Typography color="#374151" sx={{ fontSize: 13 }}>
            Fundraising CRM
          </Typography>
        </Breadcrumbs>

        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
          }}
        >
          <Typography
            variant="h5"
            sx={{ fontWeight: 700, color: '#1a1a1a' }}
          >
            Fundraising
          </Typography>

          <Button
            variant="contained"
            size="small"
            startIcon={
              exporting
                ? <CircularProgress size={14} sx={{ color: '#ffffff' }} />
                : <Download size={14} />
            }
            disabled={shortlists.length === 0 || exporting || isLoading}
            onClick={handleExportCsv}
            sx={{
              bgcolor: '#16a34a',
              color: '#ffffff',
              textTransform: 'none',
              fontSize: '0.8rem',
              fontWeight: 600,
              px: 2,
              py: 0.75,
              borderRadius: 1.5,
              '&:hover': { bgcolor: '#15803d' },
              '&.Mui-disabled': {
                bgcolor: '#d1d5db',
                color: '#9ca3af',
              },
            }}
          >
            {exporting ? 'Exporting...' : 'Export CSV'}
          </Button>
        </Box>
      </Box>

      {/* Board */}
      <Box sx={{ flex: 1, px: 2, overflow: 'hidden' }}>
        <KanbanBoard
          stages={stages}
          shortlists={shortlists}
          isLoading={isLoading}
          onDrop={handleDrop}
          onCardClick={handleCardClick}
        />
      </Box>

      {/* Detail sidebar */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={handleCloseDrawer}
        PaperProps={{
          sx: {
            width: SIDEBAR_WIDTH,
            bgcolor: '#ffffff',
            borderLeft: '1px solid #e5e7eb',
          },
        }}
      >
        {selectedShortlist && (
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Sidebar header */}
            <Box
              sx={{
                px: 2.5,
                py: 2,
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                borderBottom: '1px solid #e5e7eb',
              }}
            >
              <Box sx={{ flex: 1, mr: 1 }}>
                <Typography
                  variant="h6"
                  sx={{ fontWeight: 700, color: '#1a1a1a', fontSize: '1.05rem' }}
                >
                  {selectedShortlist.investor_name || 'Unknown Investor'}
                </Typography>
                {selectedShortlist.investor_company && (
                  <Typography variant="body2" sx={{ color: '#6b7280', mt: 0.25 }}>
                    {selectedShortlist.investor_company}
                  </Typography>
                )}
                {selectedShortlist.investor_location && (
                  <Typography variant="caption" sx={{ color: '#9ca3af' }}>
                    {selectedShortlist.investor_location}
                  </Typography>
                )}
              </Box>
              <IconButton onClick={handleCloseDrawer} size="small" sx={{ color: '#9ca3af' }}>
                <X size={18} />
              </IconButton>
            </Box>

            {/* Scrollable content */}
            <Box sx={{ flex: 1, overflow: 'auto', px: 2.5, py: 2 }}>
              {/* Stage selector */}
              <FormControl fullWidth size="small" sx={{ mb: 2.5 }}>
                <InputLabel sx={{ color: '#6b7280' }}>Stage</InputLabel>
                <Select
                  value={selectedShortlist.stage_id || ''}
                  label="Stage"
                  onChange={(e) => handleStageChange(e.target.value as string)}
                  sx={{
                    color: '#374151',
                    '.MuiOutlinedInput-notchedOutline': {
                      borderColor: '#d1d5db',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#9ca3af',
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#4f7df9',
                    },
                  }}
                >
                  {stages.map((stage) => (
                    <MenuItem key={stage.id} value={stage.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box
                          sx={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            bgcolor: stage.color || '#3B82F6',
                          }}
                        />
                        {stage.name}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Status & notes */}
              {selectedShortlist.status && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" sx={{ color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Status
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#374151', mt: 0.25 }}>
                    {selectedShortlist.status}
                  </Typography>
                </Box>
              )}

              {selectedShortlist.notes && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" sx={{ color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Notes
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#6b7280', mt: 0.25, whiteSpace: 'pre-wrap' }}>
                    {selectedShortlist.notes}
                  </Typography>
                </Box>
              )}

              {/* Tags */}
              <Box sx={{ mb: 2.5 }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: '#9ca3af',
                    textTransform: 'uppercase',
                    letterSpacing: 0.5,
                    display: 'block',
                    mb: 0.75,
                  }}
                >
                  Tags
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selectedShortlist.tags.length === 0 && (
                    <Typography variant="caption" sx={{ color: '#d1d5db', fontStyle: 'italic' }}>
                      No tags
                    </Typography>
                  )}
                  {selectedShortlist.tags.map((tag) => (
                    <Chip
                      key={tag.id}
                      label={tag.name}
                      size="small"
                      sx={{
                        height: 24,
                        fontSize: '0.72rem',
                        bgcolor: tag.color ? `${tag.color}15` : '#eff6ff',
                        color: tag.color || '#4f7df9',
                        border: '1px solid',
                        borderColor: tag.color ? `${tag.color}30` : '#dbeafe',
                      }}
                    />
                  ))}
                </Box>
              </Box>

              <Divider sx={{ borderColor: '#e5e7eb', mb: 2 }} />

              {/* Add activity form */}
              <Box sx={{ mb: 2.5 }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: '#9ca3af',
                    textTransform: 'uppercase',
                    letterSpacing: 0.5,
                    display: 'block',
                    mb: 1,
                  }}
                >
                  Add Activity
                </Typography>
                <FormControl fullWidth size="small" sx={{ mb: 1 }}>
                  <Select
                    value={newActivityType}
                    onChange={(e) => setNewActivityType(e.target.value as string)}
                    sx={{
                      color: '#374151',
                      '.MuiOutlinedInput-notchedOutline': { borderColor: '#d1d5db' },
                      '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#9ca3af' },
                      '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#4f7df9' },
                    }}
                  >
                    {ACTIVITY_TYPES.map((at) => (
                      <MenuItem key={at.value} value={at.value}>
                        {at.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  fullWidth
                  size="small"
                  multiline
                  rows={2}
                  placeholder="Activity summary..."
                  value={newActivitySummary}
                  onChange={(e) => setNewActivitySummary(e.target.value)}
                  sx={{
                    mb: 1,
                    '& .MuiOutlinedInput-root': {
                      color: '#374151',
                      '& fieldset': { borderColor: '#d1d5db' },
                      '&:hover fieldset': { borderColor: '#9ca3af' },
                      '&.Mui-focused fieldset': { borderColor: '#4f7df9' },
                    },
                    '& .MuiInputBase-input::placeholder': {
                      color: '#9ca3af',
                    },
                  }}
                />
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<Plus size={14} />}
                  disabled={!newActivitySummary.trim() || createActivityMutation.isPending}
                  onClick={handleAddActivity}
                  sx={{
                    bgcolor: '#4f7df9',
                    color: '#ffffff',
                    fontWeight: 600,
                    textTransform: 'none',
                    '&:hover': { bgcolor: '#3b6de6' },
                    '&.Mui-disabled': {
                      bgcolor: '#e5e7eb',
                      color: '#9ca3af',
                    },
                  }}
                >
                  {createActivityMutation.isPending ? 'Adding...' : 'Add Activity'}
                </Button>
                {createActivityMutation.isError && (
                  <Alert severity="error" sx={{ mt: 1, fontSize: '0.75rem' }}>
                    Failed to add activity
                  </Alert>
                )}
              </Box>

              <Divider sx={{ borderColor: '#e5e7eb', mb: 2 }} />

              {/* Activity timeline */}
              <Box>
                <Typography
                  variant="caption"
                  sx={{
                    color: '#9ca3af',
                    textTransform: 'uppercase',
                    letterSpacing: 0.5,
                    display: 'block',
                    mb: 1.5,
                  }}
                >
                  Activity Timeline
                </Typography>

                {activitiesLoading && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <CircularProgress size={24} sx={{ color: '#4f7df9' }} />
                  </Box>
                )}

                {!activitiesLoading && activities.length === 0 && (
                  <Typography
                    variant="body2"
                    sx={{ color: '#d1d5db', fontStyle: 'italic', textAlign: 'center', py: 2 }}
                  >
                    No activities yet
                  </Typography>
                )}

                {activities.map((activity: Activity, idx: number) => (
                  <Box
                    key={activity.id}
                    sx={{
                      display: 'flex',
                      gap: 1.5,
                      mb: idx < activities.length - 1 ? 2 : 0,
                      position: 'relative',
                      ...(idx < activities.length - 1 && {
                        '&::before': {
                          content: '""',
                          position: 'absolute',
                          left: 11,
                          top: 28,
                          bottom: -16,
                          width: 1,
                          bgcolor: '#e5e7eb',
                        },
                      }),
                    }}
                  >
                    {/* Icon */}
                    <Box
                      sx={{
                        width: 24,
                        height: 24,
                        borderRadius: '50%',
                        bgcolor: '#eff6ff',
                        color: '#4f7df9',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        mt: 0.25,
                      }}
                    >
                      {getActivityIcon(activity.activity_type)}
                    </Box>

                    {/* Content */}
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.25 }}>
                        <Chip
                          label={activity.activity_type}
                          size="small"
                          sx={{
                            height: 18,
                            fontSize: '0.6rem',
                            textTransform: 'capitalize',
                            bgcolor: '#f3f4f6',
                            color: '#6b7280',
                            '& .MuiChip-label': { px: 0.5 },
                          }}
                        />
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
                          <Clock size={10} style={{ color: '#9ca3af' }} />
                          <Typography
                            variant="caption"
                            sx={{ color: '#9ca3af', fontSize: '0.65rem' }}
                          >
                            {formatDate(activity.date)}
                          </Typography>
                        </Box>
                      </Box>
                      {activity.summary && (
                        <Typography
                          variant="body2"
                          sx={{ color: '#374151', fontSize: '0.8rem' }}
                        >
                          {activity.summary}
                        </Typography>
                      )}
                      {activity.details && (
                        <Typography
                          variant="caption"
                          sx={{
                            color: '#9ca3af',
                            display: 'block',
                            mt: 0.25,
                          }}
                        >
                          {activity.details}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        )}
      </Drawer>
    </Box>
  );
};

export default KanbanPage;
