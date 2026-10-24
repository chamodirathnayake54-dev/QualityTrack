import { useRef, useState } from 'react';
import { useInfiniteQuery, useIsMutating, useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../../api/client';
import type { Page } from '../../api/defects';
import type { Action, Cause, DefectEvent } from '../../api/workflow';
import { useWorkflowPages, useWorkflowRecord } from './useWorkflow';

type RecordState = ReturnType<typeof useWorkflowRecord>;
type Evidence = 'completion_notes' | 'reopen_reason';
type Transition = { label: string; target: string; evidence?: Evidence };
export type ActionEvent = DefectEvent & { completion_notes: string | null; reopen_reason: string | null };
export type TransitionOptions = Transition & {
  record: RecordState; actionId?: string; ready: boolean; context: string;
  refresh: () => Promise<unknown>; reportSuccess: (message: string) => void;
};

// PUBLIC_INTERFACE
export function transitionChoices(status: string, permissions: readonly string[], action = false): Transition[] {
  /** Map saved status and explicit grants to presentation choices; the API remains authoritative. */
  const choices: (Transition & { permission: string })[] = action
    ? [
      ...(status === 'Open' ? [{ label: 'Start action', target: 'In Progress', permission: 'action.progress' }] : []),
      ...(status !== 'Complete' ? [{ label: 'Complete action', target: 'Complete', permission: 'action.complete', evidence: 'completion_notes' as const }] : []),
      ...(status === 'Complete' ? [{ label: 'Reopen action', target: 'In Progress', permission: 'action.reopen', evidence: 'reopen_reason' as const }] : []),
    ]
    : [
      ...(status === 'Under Investigation' ? [{ label: 'Close defect', target: 'Closed', permission: 'defect.close' }] : []),
      ...(status === 'Closed' ? [{ label: 'Reopen defect', target: 'Under Investigation', permission: 'defect.reopen' }] : []),
    ];
  return choices.filter((choice) => permissions.includes(choice.permission))
    .map(({ label, target, evidence }) => ({ label, target, evidence }));
}

// PUBLIC_INTERFACE
export function useTransition({ record, label, target, actionId, evidence, ready, context, refresh, reportSuccess }: TransitionOptions) {
  /** Validate notes and reviewed parent revision, serialize a single POST, and require renewed review after errors. */
  const queryClient = useQueryClient();
  const [review, setReview] = useState<{ etag: string; context: string } | null>(null);
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const lock = useRef(false);
  const mutationKey = ['workflow-write', record.identity?.ref, record.defectId];
  const pending = useIsMutating({ mutationKey }) > 0;
  const mutation = useMutation({
    mutationKey, retry: false,
    mutationFn: ({ etag, body }: { etag: string; body: unknown }) => record.client.request(
      actionId ? `/actions/${encodeURIComponent(actionId)}/transitions` : `${record.base}/transitions`,
      { method: 'POST', etag, body },
    ),
  });
  const checked = Boolean(review && review.etag === record.parent.data?.etag && review.context === context);
  const available = ready && !record.parent.isFetching && !pending;
  const reload = async () => {
    setReview(null);
    await refresh();
  };
  const submit = async () => {
    if (lock.current || pending || !available) return;
    if (!checked || !review || !/^"[0-9]+"$/.test(review.etag)) {
      setMessage('Reload latest details, then check them and tick the box before confirming.');
      return;
    }
    if (evidence && (!notes.trim() || notes.trim().length > 2000)) {
      setMessage('Add notes between 1 and 2000 characters before confirming.');
      return;
    }
    lock.current = true;
    setSuccess(false);
    setMessage('');
    try {
      await mutation.mutateAsync({
        etag: review.etag,
        body: { target_status: target, ...(evidence ? { [evidence]: notes.trim() } : {}) },
      });
      setSuccess(true);
      setMessage(`${label} saved.`);
      reportSuccess(`${label} saved.`);
      setNotes('');
      setReview(null);
      await refresh();
      void queryClient.invalidateQueries({ queryKey: ['defects', record.identity?.ref] });
    } catch (error) {
      setReview(null);
      if (error instanceof ApiError) {
        setMessage(error.uncertain
          ? "We couldn't confirm whether this was saved. Please check the page before trying again so nothing is saved twice."
          : error.problem.code === 'actions_incomplete' && target === 'Closed'
            ? "This can't be closed yet: all corrective actions must be completed first."
            : error.message);
        if (error.uncertain || [400, 409, 412, 428].includes(error.problem.status)) await refresh();
      } else setMessage("We couldn't save this change. Please check the latest details before trying again.");
    } finally {
      lock.current = false;
    }
  };
  return {
    notes, setNotes, message, success, pending, checked, available, submit, reload,
    confirmDisabled: !available || !checked,
    review: (value: boolean) => setReview(value && available && record.parent.data?.etag
      ? { etag: record.parent.data.etag, context } : null),
  };
}

// PUBLIC_INTERFACE
export function useActionSummary(action: Action, record: RecordState, context: string, ready: boolean) {
  /** Load action evidence and prepare grant/status choices without deriving revision from the action. */
  const history = useInfiniteQuery({
    queryKey: ['action-history', record.identity?.ref, record.defectId, action.id],
    initialPageParam: '',
    queryFn: async ({ signal, pageParam }) => (await record.client.request<Page<ActionEvent>>(
      `/actions/${encodeURIComponent(action.id)}/history?${new URLSearchParams({ limit: '50', ...(pageParam ? { cursor: pageParam } : {}) })}`,
      { signal },
    )).data,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
  });
  return {
    history, choices: transitionChoices(action.status, record.identity?.permissions ?? [], true),
    ready: ready && history.isSuccess && !history.isFetching,
    context: JSON.stringify([context, action, history.data]),
  };
}

// PUBLIC_INTERFACE
export function useDefectSummary() {
  /** Prepare summary collections, navigation grants and explicit refresh for reviewed transitions. */
  const record = useWorkflowRecord();
  const [successMessage, setSuccessMessage] = useState('');
  const causes = useWorkflowPages<Cause>(record, 'causes');
  const actions = useWorkflowPages<Action>(record, 'actions');
  const history = useWorkflowPages<DefectEvent>(record, 'history');
  const queryClient = useQueryClient();
  const ready = [causes, actions, history].every((query) => query.isSuccess && !query.isFetching);
  const context = JSON.stringify([record.parent.data, causes.data, actions.data, history.data]);
  const refresh = async () => {
    await Promise.all([record.parent.refetch(), causes.refetch(), actions.refetch(), history.refetch(),
      queryClient.invalidateQueries({ queryKey: ['action-history', record.identity?.ref, record.defectId] })]);
  };
  const permissions = record.identity?.permissions ?? [];
  const links = [
    { permission: 'cause.create', path: 'causes', label: 'Record cause' },
    { permission: 'defect.investigate', path: 'investigation', label: 'Investigation' },
    { permission: 'action.assign', path: 'actions', label: 'Add corrective action' },
  ].filter((link) => permissions.includes(link.permission));
  return {
    record, causes, actions, history, ready, context, refresh, links, successMessage, setSuccessMessage,
    choices: transitionChoices(record.parent.data?.data.status ?? '', permissions),
  };
}
