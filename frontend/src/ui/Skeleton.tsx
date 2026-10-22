// PUBLIC_INTERFACE
export function Skeleton({ label = 'Loading…' }: { label?: string }) {
  /** Announce a labelled read-in-progress state with motion-safe decoration. */
  return <div role="status" className="rounded-control bg-canvas p-4">
    <span className="motion-safe:animate-pulse">{label}</span>
  </div>;
}
