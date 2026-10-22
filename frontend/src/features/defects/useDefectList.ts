import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import type { Defect, Page } from '../../api/defects';
import { useAuth } from '../auth/AuthProvider';
import { useLookups } from './useCapture';
import { validateFilters } from './validation';

const supported = ['status', 'severity', 'production_line_id', 'shift_id', 'defect_type_id',
  'part_number', 'start_date', 'end_date', 'limit', 'cursor'];

// PUBLIC_INTERFACE
export function useDefectList() {
  /** Own live list queries and opaque continuation; filter changes always discard the cursor. */
  const { client, identity } = useAuth();
  const [search, setSearch] = useSearchParams();
  const params = new URLSearchParams();
  supported.forEach((key) => { const value = search.get(key); if (value) params.set(key, value); });
  const errors = validateFilters(params);
  const queryString = params.toString();
  const query = useQuery({
    queryKey: ['defects', identity?.ref, queryString],
    queryFn: async ({ signal }) => (await client.request<Page<Defect>>(`/defects?${queryString}`, { signal })).data,
    enabled: !Object.keys(errors).length,
    retry: false,
  });
  const lookups = useLookups();
  const apply = (form: HTMLFormElement) => {
    const next = new URLSearchParams();
    new FormData(form).forEach((value, key) => { if (typeof value === 'string' && value.trim()) next.set(key, value.trim()); });
    setSearch(next);
  };
  const nextPage = () => {
    if (!query.data?.next_cursor) return;
    const next = new URLSearchParams(params);
    next.set('cursor', query.data.next_cursor);
    setSearch(next);
  };
  const firstPage = () => {
    const next = new URLSearchParams(params);
    next.delete('cursor');
    setSearch(next);
  };
  return { query, lookups, params, errors, apply, nextPage, firstPage,
    canCapture: Boolean(identity?.permissions.includes('defect.capture')), zone: identity?.plant_zone };
}
