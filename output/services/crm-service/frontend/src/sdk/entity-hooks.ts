// =============================================================================
// Entity Registry SDK — React Query Hooks
// Generated: 2026-03-10T13:09:26.217926Z
// =============================================================================

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query';
import { entityClient, type ListParams, type ListResponse, type DropdownOption } from './entity-api-client';
import { getEntity, type EntityFieldMeta } from './entity-registry';

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const entityKeys = {
  all: (entity: string) => [entity] as const,
  lists: (entity: string) => [entity, 'list'] as const,
  list: (entity: string, params?: ListParams) => [entity, 'list', params] as const,
  details: (entity: string) => [entity, 'detail'] as const,
  detail: (entity: string, id: string) => [entity, 'detail', id] as const,
  options: (entity: string) => [entity, 'options'] as const,
  fkOptions: (endpoint: string) => ['fk-options', endpoint] as const,
};

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/** Fetch a paginated list of entity records. */
export function useEntityList<T = Record<string, unknown>>(
  entity: string,
  params?: ListParams,
  options?: Omit<UseQueryOptions<ListResponse<T>>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<ListResponse<T>>({
    queryKey: entityKeys.list(entity, params),
    queryFn: () => entityClient.list<T>(entity, params),
    ...options,
  });
}

/** Fetch a single entity record by ID. */
export function useEntityDetail<T = Record<string, unknown>>(
  entity: string,
  id: string | undefined,
  options?: Omit<UseQueryOptions<T>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<T>({
    queryKey: entityKeys.detail(entity, id ?? ''),
    queryFn: () => entityClient.get<T>(entity, id!),
    enabled: !!id,
    ...options,
  });
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/** Create a new entity record. Invalidates list cache on success. */
export function useEntityCreate<T = Record<string, unknown>>(
  entity: string,
  options?: UseMutationOptions<T, Error, Record<string, unknown>>,
) {
  const queryClient = useQueryClient();
  return useMutation<T, Error, Record<string, unknown>>({
    mutationFn: (data) => entityClient.create<T>(entity, data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.lists(entity) });
      options?.onSuccess?.(...args);
    },
    ...options,
  });
}

/** Update an existing entity record. Invalidates list + detail cache. */
export function useEntityUpdate<T = Record<string, unknown>>(
  entity: string,
  options?: UseMutationOptions<T, Error, { id: string; data: Record<string, unknown> }>,
) {
  const queryClient = useQueryClient();
  return useMutation<T, Error, { id: string; data: Record<string, unknown> }>({
    mutationFn: ({ id, data }) => entityClient.update<T>(entity, id, data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.lists(entity) });
      const id = args[1]?.id;
      if (id) {
        queryClient.invalidateQueries({ queryKey: entityKeys.detail(entity, id) });
      }
      options?.onSuccess?.(...args);
    },
    ...options,
  });
}

/** Delete an entity record. Invalidates list cache on success. */
export function useEntityDelete(
  entity: string,
  options?: UseMutationOptions<void, Error, string>,
) {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => entityClient.delete(entity, id),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.lists(entity) });
      options?.onSuccess?.(...args);
    },
    ...options,
  });
}

// ---------------------------------------------------------------------------
// Dropdown / FK hooks
// ---------------------------------------------------------------------------

/** Load dropdown options for an entity (id + labelField). */
export function useEntityDropdown(
  entity: string,
  labelField?: string,
  options?: Omit<UseQueryOptions<DropdownOption[]>, 'queryKey' | 'queryFn'>,
) {
  const meta = getEntity(entity);
  const lf = labelField ?? meta.labelField;

  return useQuery<DropdownOption[]>({
    queryKey: entityKeys.options(entity),
    queryFn: async () => {
      const res = await entityClient.list(entity, { page_size: 200 });
      return res.items.map((item) => ({
        value: String(item['id'] ?? ''),
        label: String(item[lf] ?? item['id'] ?? ''),
      }));
    },
    staleTime: 10 * 60 * 1000, // 10 min — FK options rarely change
    refetchOnMount: false,
    ...options,
  });
}

/** Load dropdown options for a specific FK field using its metadata. */
export function useFKOptions(
  fieldMeta: EntityFieldMeta | undefined,
  options?: Omit<UseQueryOptions<DropdownOption[]>, 'queryKey' | 'queryFn'>,
) {
  const endpoint = fieldMeta?.fk?.endpoint ?? '';

  return useQuery<DropdownOption[]>({
    queryKey: entityKeys.fkOptions(endpoint),
    queryFn: () => entityClient.loadOptions(fieldMeta!),
    enabled: !!fieldMeta?.fk,
    staleTime: 10 * 60 * 1000, // 10 min — FK options rarely change
    refetchOnMount: false,
    ...options,
  });
}
