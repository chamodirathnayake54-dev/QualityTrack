import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import {
  Alert, Button, DataTable, DateInput, EmptyState, ErrorSummary, Field,
  Journey, RadioGroup, Select, Skeleton, StatusBadge, TextArea, TextInput,
} from './index';

describe('shared UI', () => {
  it('preserves badge labels with supplementary tones and a neutral fallback', () => {
    render(<><StatusBadge>Critical</StatusBadge><StatusBadge>Unknown status</StatusBadge></>);
    expect(screen.getByText('Critical')).toHaveClass('whitespace-nowrap', 'text-red-900');
    expect(screen.getByText('Unknown status')).toHaveClass('text-ink');
  });

  it('exposes current and saved journey progress without changing destinations', () => {
    render(<MemoryRouter><Journey current={1} steps={[
      { href: '/causes', label: 'Cause', complete: true },
      { href: '/investigation', label: 'Investigation', complete: false },
      { href: '/actions', label: 'Action', complete: false },
    ]} /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Cause' })).toHaveAttribute('href', '/causes');
    expect(screen.getByRole('link', { name: 'Investigation' })).toHaveAttribute('aria-current', 'step');
    expect(screen.getByRole('link', { name: 'Action' })).not.toHaveAttribute('aria-current');
    expect(screen.getByText('Finished')).toBeVisible();
  });

  it('links labels, hints and invalid feedback to text controls', () => {
    render(<Field label="Part" hint="Use the printed code" error="Required">
      {(props) => <TextInput {...props} />}</Field>);
    const input = screen.getByLabelText('Part');
    expect(input).toHaveAccessibleDescription('Use the printed code Required');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('preserves native textarea, select, and date behavior', async () => {
    const user = userEvent.setup();
    render(<>
      <Field label="Notes">{(props) => <TextArea {...props} />}</Field>
      <Field label="Shift">{(props) => <Select {...props}>
        <option value="">Choose</option><option value="day">Day</option>
      </Select>}</Field>
      <Field label="Due">{(props) => <DateInput {...props} defaultValue="2026-10-22" />}</Field>
    </>);
    await user.type(screen.getByLabelText('Notes'), 'Preliminary evidence');
    await user.selectOptions(screen.getByLabelText('Shift'), 'day');
    expect(screen.getByLabelText('Notes')).toHaveValue('Preliminary evidence');
    expect(screen.getByLabelText('Shift')).toHaveValue('day');
    expect(screen.getByLabelText('Due')).toHaveValue('2026-10-22');
  });

  it('prevents clicks on pending buttons and exposes busy state', async () => {
    const click = vi.fn();
    render(<Button pending onClick={click}>Saving…</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(click).not.toHaveBeenCalled();
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });

  it('supports native keyboard radio selection without a hidden default', async () => {
    function Example() {
      const [value, setValue] = useState('');
      return <RadioGroup legend="Severity" name="severity" value={value} onChange={setValue}
        error="Choose a severity" options={[{ value: 'Major', label: 'Major' }, { value: 'Minor', label: 'Minor' }]} />;
    }
    render(<Example />);
    expect(screen.getByRole('group')).toHaveAccessibleDescription('Choose a severity');
    expect(screen.getAllByRole('radio').every((radio) => !(radio as HTMLInputElement).checked)).toBe(true);
    await userEvent.tab();
    await userEvent.keyboard(' ');
    expect(screen.getByLabelText('Major')).toBeChecked();
    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByLabelText('Minor')).toBeChecked();
  });

  it('focuses the error summary and renders a field link', () => {
    render(<ErrorSummary errors={[{ label: 'Check part', href: '#part' }]} />);
    expect(screen.getByRole('alert')).toHaveFocus();
    expect(screen.getByRole('link', { name: 'Check part' })).toHaveAttribute('href', '#part');
  });

  it('renders textual feedback, loading, empty, status, and table semantics', () => {
    render(<>
      <Alert tone="danger">Access denied</Alert>
      <Alert tone="success">Saved</Alert>
      <Skeleton label="Loading context…" />
      <EmptyState title="No entries"><p>Add one when permitted.</p></EmptyState>
      <StatusBadge>Under Investigation</StatusBadge>
      <DataTable caption="Records" columns={[{ key: 'part', heading: 'Part', render: (row: { id: string }) => row.id }]}
        rows={[{ id: 'P-1' }]} rowKey={(row) => row.id} />
    </>);
    expect(screen.getByRole('alert')).toHaveTextContent('Access denied');
    expect(screen.getAllByRole('status')).toHaveLength(2);
    expect(screen.getByRole('heading', { name: 'No entries' })).toBeVisible();
    expect(screen.getByText('Under Investigation')).toBeVisible();
    expect(screen.getByRole('region', { name: 'Records' })).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('table', { name: 'Records' })).toBeVisible();
    expect(screen.getByRole('columnheader')).toHaveTextContent('Part');
    expect(screen.getByRole('cell')).toHaveTextContent('P-1');
  });
});
