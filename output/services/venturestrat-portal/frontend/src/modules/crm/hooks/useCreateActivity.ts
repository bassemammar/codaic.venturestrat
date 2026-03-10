import { useMutation, useQueryClient } from '@tanstack/react-query';
import { crmApi } from '../api/crmApi';
import type { Activity, ActivityCreateRequest } from '@crm/types/activity.types';

/**
 * Mutation hook to create a new activity on a shortlist.
 * Invalidates both the activities query and the user-shortlists query.
 */
export function useCreateActivity() {
  const queryClient = useQueryClient();

  return useMutation<Activity, Error, ActivityCreateRequest>({
    mutationFn: (data) => crmApi.createActivity(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['crm', 'activities', variables.shortlist_id],
      });
      queryClient.invalidateQueries({ queryKey: ['crm', 'user-shortlists'] });
    },
  });
}
