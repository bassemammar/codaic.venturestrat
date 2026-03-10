/**
 * useEmailAccounts — fetches and manages OAuth-connected email accounts.
 *
 * Provides:
 *   - useConnectedAccounts(userId) — query for OAuth-connected accounts
 *   - useDisconnectAccount() — mutation to remove a connected account
 *   - useGoogleConnect(userId) — initiates Google OAuth flow
 *   - useMicrosoftConnect(userId) — initiates Microsoft OAuth flow
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchEmailAccounts } from '../api/outreachApi';
import {
  getConnectedAccounts,
  disconnectAccount,
  getGoogleAuthUrl,
  getMicrosoftAuthUrl,
  type ConnectedAccount,
} from '../api/outreachApi';

// ---------------------------------------------------------------------------
// Legacy: CRUD email accounts from outreach-service entities
// ---------------------------------------------------------------------------

export function useEmailAccounts() {
  return useQuery({
    queryKey: ['outreach', 'emailAccounts'],
    queryFn: fetchEmailAccounts,
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// OAuth-connected accounts
// ---------------------------------------------------------------------------

export function useConnectedAccounts(userId?: string) {
  return useQuery<ConnectedAccount[]>({
    queryKey: ['oauth', 'connectedAccounts', userId],
    queryFn: () => getConnectedAccounts(userId),
    staleTime: 30_000,
    retry: false,
  });
}

export function useDisconnectAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (accountId: string) => disconnectAccount(accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth', 'connectedAccounts'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Initiate OAuth flows — opens auth URL in current tab
// ---------------------------------------------------------------------------

export function useGoogleConnect(userId?: string) {
  return useMutation({
    mutationFn: async () => {
      const { authorization_url } = await getGoogleAuthUrl(userId);
      window.location.href = authorization_url;
    },
  });
}

export function useMicrosoftConnect(userId?: string) {
  return useMutation({
    mutationFn: async () => {
      const { authorization_url } = await getMicrosoftAuthUrl(userId);
      window.location.href = authorization_url;
    },
  });
}
