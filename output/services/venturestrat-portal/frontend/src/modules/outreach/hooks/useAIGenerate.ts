/**
 * useAIGenerate — mutation for POST /ai/generate-email
 */

import { useMutation } from '@tanstack/react-query';
import { aiGenerateEmail } from '../api/outreachApi';
import type { AIGenerateEmailRequest } from '../api/outreachApi';

export function useAIGenerate() {
  return useMutation({
    mutationFn: (payload: AIGenerateEmailRequest) => aiGenerateEmail(payload),
  });
}
