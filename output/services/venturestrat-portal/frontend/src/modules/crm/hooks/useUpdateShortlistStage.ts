import { useMutation, useQueryClient } from '@tanstack/react-query';
import { crmApi } from '../api/crmApi';
import type { Shortlist } from '@crm/types/shortlist.types';

interface UpdateStageParams {
  shortlistId: string;
  stageId: string;
}

/**
 * Mutation hook to update a shortlist's pipeline stage (used on Kanban drag-and-drop).
 * Invalidates the user-shortlists query on success.
 */
export function useUpdateShortlistStage() {
  const queryClient = useQueryClient();

  return useMutation<Shortlist, Error, UpdateStageParams>({
    mutationFn: ({ shortlistId, stageId }) =>
      crmApi.updateShortlist(shortlistId, { stage_id: stageId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'user-shortlists'] });
    },
  });
}
