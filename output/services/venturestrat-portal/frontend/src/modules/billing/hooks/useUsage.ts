import { useQuery } from '@tanstack/react-query';
import type { UsageRecord } from '@bill/types/usage_record.types';
import { useAuth } from '../../../auth/AuthProvider';
import { fetchUsageRecords } from '../api/billingApi';

const USAGE_KEY = 'billing-usage';

export function useUsage() {
  const { user } = useAuth();

  return useQuery<UsageRecord[]>({
    queryKey: [USAGE_KEY, user?.id],
    queryFn: () => {
      if (!user?.id) return Promise.resolve([]);
      return fetchUsageRecords(user.id);
    },
    enabled: !!user?.id,
    staleTime: 60 * 1000,
  });
}
