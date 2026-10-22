import { Link } from 'react-router-dom';

type Step = { href: string; label: string; complete: boolean };

// PUBLIC_INTERFACE
export function Journey({ steps, current }: { steps: Step[]; current: number }) {
  /** Render existing destinations with explicit progress; never infer lifecycle gates. */
  return <ol className="journey">
    {steps.map((step, index) => <li key={step.href}>
      <Link to={step.href} aria-label={step.label} aria-current={index === current ? 'step' : undefined}>
        <span className="journey-marker" aria-hidden="true">{step.complete ? '✓' : index + 1}</span>
        <span>{step.label}
          <span className="block text-xs text-muted">
            {index === current ? 'Current step' : step.complete ? 'Finished' : `Step ${index + 1}`}
          </span>
        </span>
      </Link>
    </li>)}
  </ol>;
}
