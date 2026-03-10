import { useQuery } from '@tanstack/react-query';
import { crmApi } from '../api/crmApi';
import type { PipelineStage } from '@crm/types/pipeline_stage.types';

const THIRTY_MINUTES = 30 * 60 * 1000;

export function usePipelineStages() {
  return useQuery<PipelineStage[]>({
    queryKey: ['crm', 'pipeline-stages'],
    queryFn: () => crmApi.getPipelineStages(),
    staleTime: THIRTY_MINUTES,
    select: (data) =>
      [...data].sort((a, b) => a.sequence - b.sequence).filter((s) => s.is_active),
  });
}
