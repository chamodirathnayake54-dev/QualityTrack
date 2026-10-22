/** Saved preliminary cause, with server attribution and parent revision. */
export interface Cause {
  id: string; defect_id: string; text: string; recorded_by_ref: string; recorded_at: string; revision: number;
}
/** Saved action; due_date remains a calendar string, not an instant. */
export interface Action {
  id: string; defect_id: string; description: string; owner_ref: string;
  due_date: string; status: 'Open' | 'In Progress' | 'Complete'; revision: number;
}
/** Immutable server transition evidence. */
export interface DefectEvent {
  id: string; old_status: string; new_status: string; actor_ref: string;
  occurred_at: string; aggregate_revision: number;
}
/** Server-provided eligible owner display; no grants or credentials are exposed. */
export interface Owner {
  ref: string; display_name: string;
}
