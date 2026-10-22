import { useRef, useState } from 'react';
import { useInfiniteQuery, useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { ApiError } from '../../api/client';
import type { Defect, Page } from '../../api/defects';
import type { Action, Cause, DefectEvent, Owner } from '../../api/workflow';
import { useAuth } from '../auth/AuthProvider';
import { validateAction, validateCause, type ActionDraft } from './workflowValidation';
import type { Errors } from './validation';

// PUBLIC_INTERFACE
export function useWorkflowRecord() {
  /** Load a direct-linked parent; never replace a reviewed view on focus/reconnect. */
  const { defectId = '' } = useParams();
  const { client, identity } = useAuth();
  const base = `/defects/${encodeURIComponent(defectId)}`;
  const key = ['defect', identity?.ref, defectId];
  const parent = useQuery({
    queryKey: key, queryFn: ({ signal }) => client.request<Defect>(base, { signal }),
    retry: false, staleTime: Infinity, refetchOnMount: 'always',
    refetchOnWindowFocus: false, refetchOnReconnect: false,
  });
  return { client, identity, defectId, base, key, parent };
}

// PUBLIC_INTERFACE
export function useWorkflowPages<T>(record: ReturnType<typeof useWorkflowRecord>, kind: 'causes' | 'actions' | 'history', enabled = true) {
  /** Keep caller/parent-bound opaque continuation and independent child outcomes. */
  return useInfiniteQuery({
    queryKey: ['workflow', record.identity?.ref, record.defectId, kind],
    initialPageParam: '',
    queryFn: async ({ signal, pageParam }) => (await record.client.request<Page<T>>(
      `${record.base}/${kind}?${new URLSearchParams({ limit: '50', ...(pageParam ? { cursor: pageParam } : {}) })}`,
      { signal },
    )).data,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: enabled && record.parent.isSuccess && !record.parent.isFetching,
    retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
  });
}

// PUBLIC_INTERFACE
export function useWorkflow(kind: 'causes' | 'investigation' | 'actions') {
  /** Own draft validation, serialized writes, and explicit renewed review after conflicts. */
  const record = useWorkflowRecord();
  const causes = useWorkflowPages<Cause>(record, 'causes', kind !== 'actions');
  const actions = useWorkflowPages<Action>(record, 'actions', kind === 'actions');
  const history = useWorkflowPages<DefectEvent>(record, 'history', kind === 'investigation');
  const queryClient = useQueryClient();
  const owners = useQuery({
    queryKey: ['owners', record.identity?.ref, record.defectId],
    queryFn: async ({ signal }) => (await record.client.request<Page<Owner>>(
      `/assignable-users?${new URLSearchParams({ defect_id: record.defectId })}`, { signal },
    )).data,
    enabled: kind === 'actions' && record.parent.isSuccess && !record.parent.isFetching,
    retry: false,
  });
  const [text, setText] = useState('');
  const [draft, setDraft] = useState<ActionDraft>({
    description: '', owner_ref: '', due_date: '', status: '', completion_notes: '',
  });
  const [errors, setErrors] = useState<Errors>({});
  const [message, setMessage] = useState('');
  const [succeeded, setSucceeded] = useState(false);
  const [moved, setMoved] = useState(false);
  const [reviewed, setReviewed] = useState<string | null>(null);
  const [reviewContext, setReviewContext] = useState('');
  const context = JSON.stringify([record.parent.data, causes.data, history.data]);
  const lock = useRef(false);
  const mutationKey = ['workflow-write', record.identity?.ref, record.defectId];
  const aggregatePending = useIsMutating({ mutationKey }) > 0;
  const mutation = useMutation({
    mutationKey,
    mutationFn: ({ path, body, etag }: { path: string; body: unknown; etag?: string }) =>
      record.client.request(path, { method: 'POST', body, etag }),
    retry: false,
  });
  const refresh = async () => {
    setReviewed(null);
    // Fetch current context before asking for another explicit review. Never replay a write.
    await Promise.all([record.parent.refetch(),
      ...(kind !== 'actions' ? [causes.refetch()] : []),
      ...(kind === 'investigation' ? [history.refetch()] : []),
      ...(kind === 'actions' ? [actions.refetch()] : []),
      ...(kind === 'actions' ? [owners.refetch()] : [])]);
  };
  const strong = (value: string | null | undefined) => Boolean(value && /^"[0-9]+"$/.test(value));
  const reviewReady = record.parent.isSuccess && !record.parent.isFetching &&
    causes.isSuccess && !causes.isFetching && history.isSuccess && !history.isFetching;
  const review = (checked: boolean) => {
    setReviewed(checked && reviewReady ? record.parent.data?.etag ?? null : null);
    setReviewContext(checked ? context : '');
  };
  const submit = async () => {
    if (lock.current || aggregatePending || (kind === 'investigation' &&
        (moved || record.parent.data?.data.status === 'Under Investigation'))) return;
    let feedback: Errors = {};
    if (kind === 'causes') feedback = validateCause(text);
    if (kind === 'actions') feedback = validateAction(draft, owners.data?.items ?? []);
    if (kind === 'investigation') {
      if (!record.defectId || !strong(record.parent.data?.etag)) feedback.revision = 'Reload latest details, then check them before trying again.';
      else if (!reviewReady || reviewed !== record.parent.data?.etag || reviewContext !== context) feedback.review = 'Review the current record and confirm before submitting.';
    }
    setErrors(feedback);
    if (Object.keys(feedback).length || !record.parent.isSuccess ||
        (kind === 'actions' && !owners.isSuccess)) return;
    lock.current = true;
    setMessage('');
    setSucceeded(false);
    try {
      if (kind === 'causes') {
        // Inspect every saved cause, including those not yet displayed.
        const normalize = (value: string) => value.trim().replace(/\s+/g, ' ').toLowerCase();
        let duplicate = false;
        let cursor: string | null = null;
        do {
          const page: Page<Cause> = (await record.client.request<Page<Cause>>(
            `${record.base}/causes?${new URLSearchParams({ limit: '50', ...(cursor ? { cursor } : {}) })}`,
          )).data;
          duplicate = page.items.some((cause) => normalize(cause.text) === normalize(text));
          cursor = page.next_cursor;
        } while (cursor && !duplicate);
        if (duplicate && !window.confirm('This cause is already recorded. Record it again?')) return;
      }
      const result = await mutation.mutateAsync({
        path: `${record.base}/${kind === 'investigation' ? 'transitions' : kind}`,
        body: kind === 'causes' ? { text: text.trim() }
          : kind === 'investigation' ? { target_status: 'Under Investigation' }
          : { description: draft.description.trim(), owner_ref: draft.owner_ref,
            due_date: draft.due_date, status: draft.status,
            ...(draft.status === 'Complete' ? { completion_notes: draft.completion_notes.trim() } : {}) },
        ...(kind === 'investigation' ? { etag: reviewed! } : {}),
      });
      // Preserve exact response metadata separately; only a full parent read can be reviewed.
      queryClient.setQueryData(['workflow-result', record.identity?.ref, record.defectId], result);
      setSucceeded(true);
      if (kind === 'investigation') setMoved(true);
      setMessage(kind === 'causes' ? 'Cause recorded' : kind === 'actions' ? 'Corrective action added' : 'Moved to Under Investigation');
      if (kind === 'causes') setText('');
      if (kind === 'actions') setDraft({ description: '', owner_ref: '', due_date: '', status: '', completion_notes: '' });
      await refresh();
      void queryClient.invalidateQueries({ queryKey: ['defects', record.identity?.ref] });
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(error.problem.field_errors ?? {});
        const status = error.problem.status;
        setMessage(error.uncertain ? "We couldn't confirm whether this was saved. Please check the page before trying again so nothing is saved twice."
          : status === 403 ? kind === 'causes' ? "You don't have permission to record causes."
            : kind === 'actions' ? "You don't have permission to add corrective actions."
            : "You don't have permission to move this defect to Under Investigation."
          : error.message);
        if (error.uncertain || [400, 409, 412, 428].includes(status)) await refresh();
      }
    } finally {
      lock.current = false;
    }
  };
  return { ...record, causes, actions, history, owners, text, setText, draft,
    update: (key: keyof ActionDraft, value: string) => setDraft((previous) => ({ ...previous, [key]: value })),
    errors, message, succeeded, submit, refresh, review, reviewReady,
    investigationReached: moved || record.parent.data?.data.status === 'Under Investigation',
    reviewed: reviewed !== null && reviewed === record.parent.data?.etag && reviewContext === context,
    pending: aggregatePending, mutationError: mutation.error };
}
