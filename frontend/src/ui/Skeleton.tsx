// PUBLIC_INTERFACE
export function Skeleton({ label = 'Loading…' }: { label?: string }) {
  /** Announce a labelled read-in-progress state with motion-safe decoration. */
  return <div role="status" className="panel space-y-3">
    <span className="text-muted">{label}</span>
    <div aria-hidden="true" className="space-y-2 motion-safe:animate-pulse">
      <div className="h-3 w-3/4 rounded-full bg-slate-200" />
      <div className="h-3 w-1/2 rounded-full bg-slate-200" />
    </div>
  </div>;
}
