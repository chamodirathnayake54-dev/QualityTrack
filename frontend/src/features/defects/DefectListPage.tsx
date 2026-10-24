import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import type { Defect } from '../../api/defects';
import { Alert, Button, DataTable, DateInput, EmptyState, ErrorSummary, Field, Select, Skeleton, StatusBadge, TextInput } from '../../ui';
import { lookupFields, severities, statuses } from './validation';
import { useDefectList } from './useDefectList';
import { plantTimeLabel } from './plantTime';

// PUBLIC_INTERFACE
export function DefectListPage() {
  /** Present live permitted records; lookup denial never hides readable list results. */
  const controller = useDefectList();
  const { query, params } = controller;
  const filterKey = params.toString();
  const [dates, setDates] = useState({ key: filterKey, start: params.get('start_date') ?? '', end: params.get('end_date') ?? '' });
  // URL changes reset the draft just as the formerly keyed date component did.
  const currentDates = dates.key === filterKey ? dates
    : { key: filterKey, start: params.get('start_date') ?? '', end: params.get('end_date') ?? '' };
  if (dates.key !== filterKey) setDates(currentDates);
  const dateError = currentDates.start && currentDates.end && currentDates.start > currentDates.end
    ? 'End date must be on or after the start date' : undefined;
  return <section className="space-y-6">
    <h1 tabIndex={-1}>Defects</h1>
    {controller.canCapture && <Link to="/defects/new">Log defect</Link>}
    <form key={params.toString()} noValidate className="space-y-4" onSubmit={(event) => {
      event.preventDefault(); controller.apply(event.currentTarget);
    }}>
      <h2>Filters</h2>
      <p>Showing defects that match all filters.</p>
      <div className="grid gap-4 md:grid-cols-3">
        <Field label="Part number">{(props) => <TextInput {...props} name="part_number" defaultValue={params.get('part_number') ?? ''} />}</Field>
        {[{ key: 'status', label: 'Status', options: statuses }, { key: 'severity', label: 'Severity', options: severities }].map((field) =>
          <Field key={field.key} label={field.label}>{(props) =>
            <Select {...props} name={field.key} defaultValue={params.get(field.key) ?? ''}>
              <option value="">All</option>{field.options.map((value) => <option key={value}>{value}</option>)}
            </Select>}</Field>)}
        {lookupFields.map((field, index) => {
          const lookup = controller.lookups[index];
          // Unavailable capture-only selectors are omitted, not a prerequisite for list access.
          return lookup.isSuccess ? <Field key={field.key} label={field.label}>{(props) =>
            <Select {...props} name={field.key} defaultValue={params.get(field.key) ?? ''}>
              <option value="">All</option>
              {params.get(field.key) && !lookup.data.items.some((item) => item.id === params.get(field.key)) &&
                <option value={params.get(field.key)!}>Current filter (not an active capture choice)</option>}
              {lookup.data.items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </Select>}</Field> : null;
        })}
        <Field label="Start date">{(props) => <DateInput {...props} name="start_date" value={currentDates.start}
          max={currentDates.end || undefined} onChange={(event) => setDates({ ...currentDates, start: event.target.value })} />}</Field>
        <Field label="End date" error={dateError}>{(props) => <DateInput {...props} name="end_date" value={currentDates.end}
          min={currentDates.start || undefined} onChange={(event) => setDates({ ...currentDates, end: event.target.value })} />}</Field>
        <Field label="Page size" error={controller.errors.limit}>{(props) =>
          <TextInput {...props} name="limit" type="number" min={1} max={100} step={1} defaultValue={params.get('limit') ?? '50'} />}</Field>
      </div>
      <p className="text-sm text-muted">Dates use plant time ({plantTimeLabel(controller.zone)}); the start and end day are both included.</p>
      <Button type="submit">Apply filters</Button>{' '}<Link to="/defects">Clear filters</Link>
    </form>
    <ErrorSummary errors={Object.values(controller.errors).map((label) => ({ label }))} />
    {!Object.keys(controller.errors).length && <>
      {query.isPending ? <Skeleton label="Loading defects…" /> : query.isError ? <Alert tone="danger">
        <p>{query.error instanceof ApiError && query.error.problem.status === 403
          ? "You don't have permission to read defects." : query.error.message}</p>
        {!(query.error instanceof ApiError && query.error.problem.status === 403) &&
          <Button onClick={() => { void query.refetch(); }}>Retry defects</Button>}
      </Alert> : query.data && <>
        {query.data.items.length ? <DataTable<Defect> caption="Defects" rows={query.data.items} rowKey={(row) => row.id}
          columns={[
            { key: 'part', heading: 'Part number', render: (row) => <Link to={`/defects/${encodeURIComponent(row.id)}`}>{row.part_number}</Link> },
            { key: 'type', heading: 'Defect type', render: (row) => row.defect_type.label_at_capture },
            { key: 'quantity', heading: 'Quantity affected', render: (row) => row.quantity_affected },
            { key: 'line', heading: 'Production line', render: (row) => row.production_line.label_at_capture },
            { key: 'shift', heading: 'Shift', render: (row) => row.shift.label_at_capture },
            { key: 'severity', heading: 'Severity', render: (row) => <StatusBadge>{row.severity}</StatusBadge> },
            { key: 'status', heading: 'Status', render: (row) => <StatusBadge>{row.status}</StatusBadge> },
            { key: 'created', heading: 'Logged on', render: (row) =>
              new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: controller.zone }).format(new Date(row.created_at)) },
          ]} /> : <EmptyState title="No matching defects">
          <p>No defects match these filters. Try clearing a filter.</p>{controller.canCapture && <Link to="/defects/new">Log a defect</Link>}
        </EmptyState>}
      </>}
    </>}
    <p>Showing {query.data?.items.length ?? 0} defects</p>
    <nav aria-label="Defect pagination" className="flex gap-4">
      <Button disabled={!params.has('cursor') || query.isFetching} onClick={controller.firstPage}>First</Button>
      <Button disabled={!controller.canPrevious || query.isFetching} onClick={controller.previousPage}>Previous</Button>
      <Button disabled={!query.data?.next_cursor || query.isFetching || Boolean(Object.keys(controller.errors).length)} onClick={controller.nextPage}>Next</Button>
    </nav>
  </section>;
}
