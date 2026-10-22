import { useRef, useState } from 'react';
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../../api/client';
import { captureDefect, type Capture, type Defect, type Lookup, type Page } from '../../api/defects';
import type { ApiResult } from '../../api/contracts';
import { useAuth } from '../auth/AuthProvider';
import { lookupFields, validateCapture, type Choices, type Draft, type Errors } from './validation';

// PUBLIC_INTERFACE
export function useLookups() {
  /** Load each capture-only lookup independently; denial never gates the defect list. */
  const { client, identity } = useAuth();
  return useQueries({ queries: lookupFields.map((field) => ({
    queryKey: ['lookups', identity?.ref, field.key],
    queryFn: async ({ signal }: { signal: AbortSignal }) =>
      (await client.request<Page<Lookup>>(field.path, { signal })).data,
    retry: false,
  })) });
}

// PUBLIC_INTERFACE
export function useCapture() {
  /** Coordinate validation, one-shot writes, retained drafts and confirmed parent revisions. */
  const { client, identity } = useAuth();
  const queryClient = useQueryClient();
  const lookups = useLookups();
  const [draft, setDraft] = useState<Draft>({
    part_number: '', quantity_affected: '', defect_type_id: '',
    production_line_id: '', shift_id: '', severity: '',
  });
  const [errors, setErrors] = useState<Errors>({});
  const [saved, setSaved] = useState<ApiResult<Defect> | null>(null);
  const lock = useRef(false);
  const mutation = useMutation({ mutationFn: (capture: Capture) => captureDefect(client, capture), retry: false });
  const choices = Object.fromEntries(lookupFields.map((field, index) =>
    [field.key, lookups[index].data?.items.filter((item) => !item.retired) ?? []])) as Choices;
  const ready = lookups.every((query) => query.isSuccess && query.data.items.some((item) => !item.retired));
  const update = (key: keyof Draft, value: string) => setDraft((previous) => ({ ...previous, [key]: value }));
  const submit = async () => {
    if (lock.current || saved) return;
    const feedback = validateCapture(draft, choices);
    setErrors(feedback);
    if (Object.keys(feedback).length || !ready) return;
    lock.current = true;
    try {
      const result = await mutation.mutateAsync({
        ...draft, part_number: draft.part_number.trim(),
        quantity_affected: Number(draft.quantity_affected), severity: draft.severity as Capture['severity'],
      });
      // Store the complete response including the exact parent ETag, never one inferred from a list.
      queryClient.setQueryData(['defect', identity?.ref, result.data.id], result);
      void queryClient.invalidateQueries({ queryKey: ['defects', identity?.ref] });
      setSaved(result);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(error.problem.field_errors ?? {});
        if (error.problem.status === 409) lookups.forEach((query) => { void query.refetch(); });
      }
    } finally {
      lock.current = false;
    }
  };
  return { draft, errors, choices, lookups, ready, update, submit, saved,
    pending: mutation.isPending, error: mutation.error };
}
