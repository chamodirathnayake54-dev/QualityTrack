import { Link } from 'react-router-dom';

type Step = { key: string; label: string; href: string; complete: boolean };

// PUBLIC_INTERFACE
export function Journey({ steps, current, backHref }: {
  steps: Step[]; current: string; backHref: string;
}) {
  /** Present caller-supplied progress without deciding workflow eligibility. */
  return <nav aria-label="Defect journey" className="space-y-3">
    <Link to={backHref}>Back to defect</Link>
    <ol className="journey">
      {steps.map((step, index) => <li key={step.key}>
        <Link to={step.href} aria-label={step.label}
          aria-describedby={step.key === current || step.complete ? `journey-${step.key}` : undefined}
          aria-current={step.key === current ? 'step' : undefined}>
          <span aria-hidden="true" className="font-semibold">{step.complete ? '✓' : index + 1}</span>
          {step.label}
          {step.key === current
            ? <span id={`journey-${step.key}`} className="sr-only">Current step</span>
            : step.complete && <span id={`journey-${step.key}`} className="text-sm text-success"> — completed</span>}
        </Link>
      </li>)}
    </ol>
  </nav>;
}
