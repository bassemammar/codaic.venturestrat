import { useQuery } from '@tanstack/react-query';
import type { Investor } from '@inve/types/investor.types';
import {
  fetchInvestorById,
  fetchInvestorEmails,
  fetchInvestorMarkets,
  fetchInvestorPastInvestments,
  fetchMarkets,
  fetchPastInvestments,
} from '../api/investorSearchApi';

const INVESTOR_DETAIL_KEY = 'investor-detail';

export interface InvestorDetailData {
  investor: Investor;
  emails: Array<{ id: string; email: string; status: string }>;
  markets: Array<{ id: string; title: string }>;
  pastInvestments: Array<{ id: string; title: string }>;
}

async function fetchInvestorDetail(id: string): Promise<InvestorDetailData> {
  const [investor, emails, investorMarkets, investorPastInvs, allMarkets, allPastInvs] =
    await Promise.all([
      fetchInvestorById(id),
      fetchInvestorEmails(id),
      fetchInvestorMarkets(id),
      fetchInvestorPastInvestments(id),
      fetchMarkets(),
      fetchPastInvestments(),
    ]);

  // Resolve market names from junction
  const marketMap = new Map(allMarkets.map((m) => [m.id, m.title]));
  const markets = investorMarkets.map((im) => ({
    id: im.market_id,
    title: marketMap.get(im.market_id) ?? im.market_id,
  }));

  // Resolve past investment names from junction
  const piMap = new Map(allPastInvs.map((p) => [p.id, p.title]));
  const pastInvestments = investorPastInvs.map((ipi) => ({
    id: ipi.past_investment_id,
    title: piMap.get(ipi.past_investment_id) ?? ipi.past_investment_id,
  }));

  return { investor, emails, markets, pastInvestments };
}

export function useInvestorDetail(id: string | undefined) {
  return useQuery<InvestorDetailData>({
    queryKey: [INVESTOR_DETAIL_KEY, id],
    queryFn: () => fetchInvestorDetail(id!),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
}
