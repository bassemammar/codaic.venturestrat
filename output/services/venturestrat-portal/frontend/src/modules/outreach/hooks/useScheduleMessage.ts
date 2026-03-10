/**
 * useScheduleMessage — mutations for schedule and cancel-schedule
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { scheduleMessage, cancelSchedule } from '../api/outreachApi';
import type { ScheduleMessageRequest } from '../api/outreachApi';

export function useScheduleMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ScheduleMessageRequest }) =>
      scheduleMessage(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outreach', 'messages'] });
    },
  });
}

export function useCancelSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => cancelSchedule(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outreach', 'messages'] });
    },
  });
}
