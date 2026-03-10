/**
 * useCreateMessage — mutation for creating draft messages (POST /messages)
 * Also useUpdateMessage for saving drafts
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createMessage, updateMessage, deleteMessage } from '../api/outreachApi';
import type { MessageCreateRequest, MessageUpdateRequest } from '@outr/types/message.types';

export function useCreateMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MessageCreateRequest) => createMessage(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outreach', 'messages'] });
    },
  });
}

export function useUpdateMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MessageUpdateRequest }) =>
      updateMessage(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outreach', 'messages'] });
    },
  });
}

export function useDeleteMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteMessage(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outreach', 'messages'] });
    },
  });
}
