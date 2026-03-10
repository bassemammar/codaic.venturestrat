import { useQuery } from '@tanstack/react-query';
import type { Plan } from '@bill/types/plan.types';
import { fetchPlans } from '../api/billingApi';

const PLANS_KEY = 'billing-plans';

export function usePlans() {
  return useQuery<Plan[]>({
    queryKey: [PLANS_KEY],
    queryFn: fetchPlans,
    staleTime: 30 * 60 * 1000,
  });
}
