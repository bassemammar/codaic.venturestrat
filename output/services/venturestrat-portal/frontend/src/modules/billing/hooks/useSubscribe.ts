import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  subscribe,
  changePlan,
  cancelSubscription,
  type SubscribeRequest,
  type SubscribeResponse,
  type ChangePlanRequest,
  type ChangePlanResponse,
  type CancelRequest,
  type CancelResponse,
} from '../api/billingApi';

export function useSubscribe() {
  const queryClient = useQueryClient();

  const subscribeMutation = useMutation<SubscribeResponse, Error, SubscribeRequest>({
    mutationFn: subscribe,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-subscription'] });
    },
  });

  const changePlanMutation = useMutation<ChangePlanResponse, Error, ChangePlanRequest>({
    mutationFn: changePlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-subscription'] });
      queryClient.invalidateQueries({ queryKey: ['billing-usage'] });
    },
  });

  const cancelMutation = useMutation<CancelResponse, Error, CancelRequest>({
    mutationFn: cancelSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-subscription'] });
    },
  });

  return {
    subscribe: subscribeMutation,
    changePlan: changePlanMutation,
    cancel: cancelMutation,
  };
}
