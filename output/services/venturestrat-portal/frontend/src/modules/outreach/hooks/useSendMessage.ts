/**
 * useSendMessage — mutation for POST /messages/{id}/send
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { sendMessage } from '../api/outreachApi';
import type { SendMessageRequest } from '../api/outreachApi';

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload?: SendMessageRequest }) =>
      sendMessage(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outreach', 'messages'] });
    },
  });
}
