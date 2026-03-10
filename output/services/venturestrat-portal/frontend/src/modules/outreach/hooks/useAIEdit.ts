/**
 * useAIEdit — mutation for POST /ai/edit-text
 */

import { useMutation } from '@tanstack/react-query';
import { aiEditText } from '../api/outreachApi';
import type { AIEditTextRequest } from '../api/outreachApi';

export function useAIEdit() {
  return useMutation({
    mutationFn: (payload: AIEditTextRequest) => aiEditText(payload),
  });
}
