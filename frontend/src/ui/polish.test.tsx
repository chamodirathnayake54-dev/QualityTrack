import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { Alert } from './Alert';
import { Journey } from './Journey';
import { StatusBadge } from './StatusBadge';

describe('presentation polish', () => {
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

  it('distinguishes current, completed and future steps while retaining destinations', () => {
    render(<MemoryRouter><Journey backHref="/defects/1" current="investigation" steps={[
      { key: 'causes', label: 'Cause', href: '/defects/1/causes', complete: true },
      { key: 'investigation', label: 'Investigation', href: '/defects/1/investigation', complete: false },
      { key: 'actions', label: 'Action', href: '/defects/1/actions', complete: false },
    ]} /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /Cause/ })).toHaveTextContent('completed');
    expect(screen.getByRole('link', { name: /Investigation/ })).toHaveAttribute('aria-current', 'step');
    expect(screen.getByRole('link', { name: 'Action' })).toHaveAttribute('href', '/defects/1/actions');
    expect(screen.getByRole('link', { name: 'Action' })).not.toHaveAttribute('aria-current');
  });
});
