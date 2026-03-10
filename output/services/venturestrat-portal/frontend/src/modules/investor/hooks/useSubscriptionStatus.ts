import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../../auth/AuthProvider';
import { fetchUserSubscription } from '../api/investorSearchApi';

const SUBSCRIPTION_STATUS_KEY = 'subscription-status';

export interface SubscriptionStatus {
  hasActiveSubscription: boolean;
  planName: string | null;
  planCode: string | null;
  limits: Record<string, number>;
  features: Record<string, any>;
  status: string | null;
  isTrialing: boolean;
  trialEndsAt: Date | null;
  daysRemaining: number | null;
  canAccess: (feature: string) => boolean;
}

function calcDaysRemaining(trialEndsAt: Date | null): number | null {
  if (!trialEndsAt) return null;
  const now = new Date();
  const msLeft = trialEndsAt.getTime() - now.getTime();
  if (msLeft <= 0) return 0;
  return Math.ceil(msLeft / (1000 * 60 * 60 * 24));
}

export function useSubscriptionStatus() {
  const { user } = useAuth();

  return useQuery<SubscriptionStatus>({
    queryKey: [SUBSCRIPTION_STATUS_KEY, user?.id],
    queryFn: async () => {
      const empty: SubscriptionStatus = {
        hasActiveSubscription: false,
        planName: null,
        planCode: null,
        limits: {},
        features: {},
        status: null,
        isTrialing: false,
        trialEndsAt: null,
        daysRemaining: null,
        canAccess: () => false,
      };

      if (!user?.id) return empty;

      const sub = await fetchUserSubscription(user.id);
      if (!sub) return empty;

      const isTrialing = sub.status === 'trialing';
      const trialEndsAt =
        sub.trial_ends_at ? new Date(sub.trial_ends_at) : null;
      const daysRemaining = isTrialing ? calcDaysRemaining(trialEndsAt) : null;
      const planCode = sub.plan?.code ?? null;
      const features = sub.plan?.features ?? {};

      const canAccess = (feature: string): boolean => {
        if (!sub) return false;
        return !!features[feature];
      };

      return {
        hasActiveSubscription: true,
        planName: sub.plan?.name ?? null,
        planCode,
        limits: sub.plan?.limits ?? {},
        features,
        status: sub.status,
        isTrialing,
        trialEndsAt,
        daysRemaining,
        canAccess,
      };
    },
    enabled: !!user?.id,
    staleTime: 5 * 60 * 1000,
  });
}
