import { useQuery } from '@tanstack/react-query';
import {
  fetchInvestorFilters,
  type InvestorFilterValues,
} from '../api/investorSearchApi';

const INVESTOR_FILTERS_KEY = 'investor-filters';

export function useInvestorFilters() {
  return useQuery<InvestorFilterValues>({
    queryKey: [INVESTOR_FILTERS_KEY],
    queryFn: fetchInvestorFilters,
    staleTime: 15 * 60 * 1000, // 15 minutes
  });
}
