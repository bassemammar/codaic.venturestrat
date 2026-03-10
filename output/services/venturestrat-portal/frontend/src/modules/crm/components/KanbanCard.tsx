import React from 'react';
import { Draggable } from '@hello-pangea/dnd';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import { Mail as MailIcon, MapPin, Building2, X as XIcon } from 'lucide-react';
import type { KanbanShortlist } from '../api/crmApi';

interface KanbanCardProps {
  shortlist: KanbanShortlist;
  index: number;
  onClick: (shortlist: KanbanShortlist) => void;
}

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

export const KanbanCard: React.FC<KanbanCardProps> = ({ shortlist, index, onClick }) => {
  const displayName = shortlist.investor_name || 'Unknown Investor';

  return (
    <Draggable draggableId={shortlist.id} index={index}>
      {(provided, snapshot) => (
        <Box
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onClick(shortlist)}
          sx={{
            bgcolor: '#ffffff',
            borderRadius: 2,
            p: 1.5,
            mb: 1,
            cursor: 'pointer',
            border: '1px solid',
            borderColor: snapshot.isDragging ? '#4f7df9' : '#e5e7eb',
            transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
            position: 'relative',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            '&:hover': {
              borderColor: '#d1d5db',
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            },
            ...(snapshot.isDragging && {
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            }),
          }}
        >
          {/* Remove button */}
          <Box
            sx={{
              position: 'absolute',
              top: 10,
              right: 10,
              color: '#d1d5db',
              cursor: 'pointer',
              '&:hover': { color: '#ef4444' },
            }}
            onClick={(e) => { e.stopPropagation(); }}
          >
            <XIcon size={14} />
          </Box>

          {/* Avatar + Name row */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, mb: 1 }}>
            <Avatar
              sx={{
                width: 36,
                height: 36,
                bgcolor: getAvatarColor(displayName),
                color: '#ffffff',
                fontSize: 14,
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              {getInitials(displayName)}
            </Avatar>
            <Typography
              variant="body2"
              sx={{
                fontWeight: 700,
                color: '#1a1a1a',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                pr: 2,
                fontSize: '0.9rem',
              }}
            >
              {displayName}
            </Typography>
          </Box>

          {/* Email */}
          {shortlist.investor_email && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
              <MailIcon size={13} color="#9ca3af" />
              <Typography
                variant="caption"
                sx={{ color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              >
                {shortlist.investor_email}
              </Typography>
            </Box>
          )}

          {/* Company */}
          {shortlist.investor_company && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
              <Building2 size={13} color="#9ca3af" />
              <Typography variant="caption" sx={{ color: '#6b7280' }}>
                {shortlist.investor_company}
              </Typography>
            </Box>
          )}

          {/* Location */}
          {shortlist.investor_location && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75 }}>
              <MapPin size={13} color="#9ca3af" />
              <Typography variant="caption" sx={{ color: '#6b7280' }}>
                {shortlist.investor_location}
              </Typography>
            </Box>
          )}

          {/* AI Email button */}
          <Button
            variant="contained"
            size="small"
            fullWidth
            sx={{
              bgcolor: '#4f7df9',
              color: '#ffffff',
              textTransform: 'none',
              fontWeight: 600,
              fontSize: 13,
              py: 0.75,
              borderRadius: 1.5,
              boxShadow: 'none',
              '&:hover': { bgcolor: '#3b6de6', boxShadow: 'none' },
            }}
            onClick={(e) => { e.stopPropagation(); }}
          >
            AI Email
          </Button>

          {/* Tags */}
          {shortlist.tags.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
              {shortlist.tags.slice(0, 3).map((tag) => (
                <Chip
                  key={tag.id}
                  label={tag.name}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.65rem',
                    bgcolor: tag.color ? `${tag.color}15` : '#eff6ff',
                    color: tag.color || '#4f7df9',
                    border: '1px solid',
                    borderColor: tag.color ? `${tag.color}30` : '#dbeafe',
                    '& .MuiChip-label': { px: 0.75 },
                  }}
                />
              ))}
              {shortlist.tags.length > 3 && (
                <Chip
                  label={`+${shortlist.tags.length - 3}`}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.65rem',
                    bgcolor: '#f3f4f6',
                    color: '#9ca3af',
                    '& .MuiChip-label': { px: 0.75 },
                  }}
                />
              )}
            </Box>
          )}
        </Box>
      )}
    </Draggable>
  );
};

export default KanbanCard;
