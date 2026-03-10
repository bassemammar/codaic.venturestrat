/**
 * useMessages — fetches messages with optional status filter
 */

import { useQuery } from '@tanstack/react-query';
import { fetchMessages } from '../api/outreachApi';
import type { MessageFilterOptions } from '@outr/types/message.types';

export function useMessages(filters?: MessageFilterOptions) {
  return useQuery({
    queryKey: ['outreach', 'messages', filters],
    queryFn: () => fetchMessages(filters),
    staleTime: 30_000,
  });
}
