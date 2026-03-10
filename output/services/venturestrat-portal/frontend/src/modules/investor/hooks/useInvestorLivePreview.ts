import { useQuery } from '@tanstack/react-query';
import type { Investor } from '@inve/types/investor.types';
import { fetchInvestorLivePreview } from '../api/investorSearchApi';

const LIVE_PREVIEW_KEY = 'investor-live-preview';

export function useInvestorLivePreview() {
  return useQuery<Investor[]>({
    queryKey: [LIVE_PREVIEW_KEY],
    queryFn: fetchInvestorLivePreview,
    staleTime: 5 * 60 * 1000,
  });
}
