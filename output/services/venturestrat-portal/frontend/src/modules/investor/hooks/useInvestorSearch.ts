import { useQuery, keepPreviousData } from '@tanstack/react-query';
import {
  searchInvestors,
  type InvestorSearchParams,
  type InvestorSearchResponse,
} from '../api/investorSearchApi';

const INVESTOR_SEARCH_KEY = 'investor-search';

export function useInvestorSearch(params: InvestorSearchParams) {
  return useQuery<InvestorSearchResponse>({
    queryKey: [INVESTOR_SEARCH_KEY, params],
    queryFn: () => searchInvestors(params),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}
