import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Alert } from './Alert';
import { StatusBadge } from './StatusBadge';

// Journey progress is exercised through WorkflowPage in workflow.test.tsx.
describe('shared presentation polish', () => {
  it.each(['Open', 'Under Investigation', 'Closed', 'Complete', 'Minor', 'Major', 'Critical'])(
    'keeps %s readable without relying on color',
    (label) => {
      render(<StatusBadge>{label}</StatusBadge>);
      expect(screen.getByText(label)).toHaveClass('whitespace-nowrap');
    },
  );

  it('retains unknown status labels', () => {
    render(<StatusBadge>Future status</StatusBadge>);
    expect(screen.getByText('Future status')).toHaveClass('text-ink');
  });

  it('adds decorative feedback icons without changing announcement semantics', () => {
    render(<Alert tone="warning">Check the latest details.</Alert>);
    expect(screen.getByRole('status')).toHaveTextContent('Check the latest details.');
    expect(screen.getByText('⚠')).toHaveAttribute('aria-hidden', 'true');
  });
});
