import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../../auth/AuthProvider';
import {
  fetchUserSubscription,
  type SubscriptionWithPlan,
} from '../api/billingApi';

const SUBSCRIPTION_KEY = 'billing-subscription';

export function useSubscription() {
  const { user } = useAuth();

  return useQuery<SubscriptionWithPlan | null>({
    queryKey: [SUBSCRIPTION_KEY, user?.id],
    queryFn: () => {
      if (!user?.id) return Promise.resolve(null);
      return fetchUserSubscription(user.id);
    },
    enabled: !!user?.id,
    staleTime: 2 * 60 * 1000,
  });
}
