/**
 * useFollowUps — TanStack Query hooks for follow-up sequences.
 *
 * Hooks:
 *   useGetFollowUps(messageId)   — query all follow-ups for a message
 *   useScheduleFollowUps()       — mutation: POST follow-up sequence
 *   useCancelFollowUp()          — mutation: DELETE (cancel) one follow-up
 *   useUpdateFollowUp()          — mutation: PUT one follow-up
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  cancelFollowUp,
  getFollowUps,
  scheduleFollowUps,
  updateFollowUp,
} from '../api/outreachApi';
import type {
  ScheduleFollowUpsRequest,
  UpdateFollowUpRequest,
} from '../api/outreachApi';

const followUpKeys = {
  all: (messageId: string) => ['outreach', 'follow-ups', messageId] as const,
};

export function useGetFollowUps(messageId: string | null | undefined) {
  return useQuery({
    queryKey: followUpKeys.all(messageId ?? ''),
    queryFn: () => getFollowUps(messageId!),
    enabled: Boolean(messageId),
    staleTime: 30_000,
  });
}

export function useScheduleFollowUps() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      messageId,
      data,
    }: {
      messageId: string;
      data: ScheduleFollowUpsRequest;
    }) => scheduleFollowUps(messageId, data),
    onSuccess: (_result, variables) => {
      qc.invalidateQueries({ queryKey: followUpKeys.all(variables.messageId) });
    },
  });
}

export function useCancelFollowUp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      followUpId,
      messageId,
    }: {
      followUpId: string;
      messageId: string;
    }) => cancelFollowUp(followUpId),
    onSuccess: (_result, variables) => {
      qc.invalidateQueries({ queryKey: followUpKeys.all(variables.messageId) });
    },
  });
}

export function useUpdateFollowUp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      followUpId,
      data,
    }: {
      followUpId: string;
      messageId: string;
      data: UpdateFollowUpRequest;
    }) => updateFollowUp(followUpId, data),
    onSuccess: (_result, variables) => {
      qc.invalidateQueries({ queryKey: followUpKeys.all(variables.messageId) });
    },
  });
}
