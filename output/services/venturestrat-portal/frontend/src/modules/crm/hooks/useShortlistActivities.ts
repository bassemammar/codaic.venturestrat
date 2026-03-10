import { useQuery } from '@tanstack/react-query';
import { crmApi } from '../api/crmApi';
import type { Activity } from '@crm/types/activity.types';

/**
 * Fetches activities for a specific shortlist, sorted descending by date.
 */
export function useShortlistActivities(shortlistId: string | null) {
  return useQuery<Activity[]>({
    queryKey: ['crm', 'activities', shortlistId],
    queryFn: () => crmApi.getActivities(shortlistId!),
    enabled: !!shortlistId,
    staleTime: 60 * 1000,
  });
}
