import React, { useMemo } from 'react';
import {
  DragDropContext,
  Droppable,
  type DropResult,
} from '@hello-pangea/dnd';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CircularProgress from '@mui/material/CircularProgress';
import { MoreVertical } from 'lucide-react';
import type { PipelineStage } from '@crm/types/pipeline_stage.types';
import type { KanbanShortlist } from '../api/crmApi';
import { KanbanCard } from './KanbanCard';

interface KanbanBoardProps {
  stages: PipelineStage[];
  shortlists: KanbanShortlist[];
  isLoading: boolean;
  onDrop: (shortlistId: string, newStageId: string) => void;
  onCardClick: (shortlist: KanbanShortlist) => void;
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({
  stages,
  shortlists,
  isLoading,
  onDrop,
  onCardClick,
}) => {
  // Group shortlists by stage_id
  const columnMap = useMemo(() => {
    const map = new Map<string, KanbanShortlist[]>();
    for (const stage of stages) {
      map.set(stage.id, []);
    }
    for (const sl of shortlists) {
      const stageId = sl.stage_id || stages[0]?.id;
      if (stageId && map.has(stageId)) {
        map.get(stageId)!.push(sl);
      }
    }
    return map;
  }, [stages, shortlists]);

  const handleDragEnd = (result: DropResult) => {
    const { draggableId, destination } = result;
    if (!destination) return;
    const newStageId = destination.droppableId;
    const currentShortlist = shortlists.find((sl) => sl.id === draggableId);
    if (currentShortlist && currentShortlist.stage_id !== newStageId) {
      onDrop(draggableId, newStageId);
    }
  };

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: 400,
        }}
      >
        <CircularProgress sx={{ color: '#4f7df9' }} />
      </Box>
    );
  }

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Box
        sx={{
          display: 'flex',
          gap: 1.5,
          overflowX: 'auto',
          pb: 2,
          minHeight: 'calc(100vh - 200px)',
          '&::-webkit-scrollbar': { height: 8 },
          '&::-webkit-scrollbar-track': { bgcolor: '#f3f4f6' },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: '#d1d5db',
            borderRadius: 4,
          },
        }}
      >
        {stages.map((stage) => {
          const items = columnMap.get(stage.id) || [];
          const stageColor = stage.color || '#3B82F6';

          return (
            <Box
              key={stage.id}
              sx={{
                minWidth: 300,
                maxWidth: 340,
                flex: '0 0 300px',
                display: 'flex',
                flexDirection: 'column',
                bgcolor: `${stageColor}08`,
                borderRadius: 2,
                overflow: 'hidden',
              }}
            >
              {/* Column header */}
              <Box
                sx={{
                  px: 1.5,
                  py: 1.25,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderBottom: '2px solid',
                  borderBottomColor: stageColor,
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      bgcolor: stageColor,
                      flexShrink: 0,
                    }}
                  />
                  <Typography
                    variant="subtitle2"
                    sx={{
                      fontWeight: 700,
                      color: '#1a1a1a',
                      fontSize: '0.95rem',
                    }}
                  >
                    {stage.name}
                  </Typography>
                  <Box
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      minWidth: 24,
                      height: 24,
                      borderRadius: '12px',
                      bgcolor: '#f3f4f6',
                      px: 0.75,
                    }}
                  >
                    <Typography
                      sx={{
                        color: '#6b7280',
                        fontWeight: 600,
                        fontSize: '0.75rem',
                      }}
                    >
                      {items.length}
                    </Typography>
                  </Box>
                </Box>
                <IconButton size="small" sx={{ color: '#9ca3af' }}>
                  <MoreVertical size={16} />
                </IconButton>
              </Box>

              {/* Droppable area */}
              <Droppable droppableId={stage.id}>
                {(provided, snapshot) => (
                  <Box
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    sx={{
                      flex: 1,
                      p: 1,
                      minHeight: 100,
                      transition: 'background-color 0.2s ease',
                      bgcolor: snapshot.isDraggingOver
                        ? `${stageColor}10`
                        : 'transparent',
                    }}
                  >
                    {items.map((sl, idx) => (
                      <KanbanCard
                        key={sl.id}
                        shortlist={sl}
                        index={idx}
                        onClick={onCardClick}
                      />
                    ))}
                    {provided.placeholder}
                    {items.length === 0 && (
                      <Typography
                        variant="caption"
                        sx={{
                          display: 'block',
                          textAlign: 'center',
                          color: '#9ca3af',
                          mt: 4,
                          fontStyle: 'italic',
                        }}
                      >
                        No investors
                      </Typography>
                    )}
                  </Box>
                )}
              </Droppable>
            </Box>
          );
        })}
      </Box>
    </DragDropContext>
  );
};

export default KanbanBoard;
