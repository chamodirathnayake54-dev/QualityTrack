import type { ApiClient } from './client';

/** Active server lookup; retired entries are never capture choices. */
export interface Lookup {
  id: string;
  code: string;
  label: string;
  retired?: boolean;
}

/** Live server page; continuation is opaque. */
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

/** Historical lookup meaning, not current configuration. */
export interface CapturedLookup {
  id: string;
  code_at_capture: string;
  label_at_capture: string;
}

/** Authoritative captured defect representation. */
export interface Defect {
  id: string;
  part_number: string;
  defect_type: CapturedLookup;
  quantity_affected: number;
  production_line: CapturedLookup;
  shift: CapturedLookup;
  severity: 'Critical' | 'Major' | 'Minor';
  status: 'Open' | 'Under Investigation' | 'Closed';
  created_by_ref: string;
  created_at: string;
  has_photo: boolean;
  revision: number;
}

/** Exact photo-free capture payload, without trusted metadata. */
export interface Capture {
  part_number: string;
  quantity_affected: number;
  defect_type_id: string;
  production_line_id: string;
  shift_id: string;
  severity: Defect['severity'];
}

// PUBLIC_INTERFACE
export function captureDefect(client: ApiClient, capture: Capture) {
  /** Send exactly one JSON-encoded capture part; browser owns the boundary. */
  const body = new FormData();
  body.append('capture', JSON.stringify(capture));
  return client.request<Defect>('/defects', { method: 'POST', body });
}
