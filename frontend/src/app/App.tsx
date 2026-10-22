import { useEffect } from 'react';
import { Navigate, NavLink, Outlet, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthProvider';
import { LoginPage } from '../features/auth/LoginPage';
import { Button, EmptyState, Skeleton } from '../ui';

function RouteFocus() {
  const location = useLocation();
  useEffect(() => {
    document.querySelector<HTMLElement>('h1')?.focus();
  }, [location.pathname]);
  return null;
}

function AuthBoundary() {
  const { identity, pending } = useAuth();
  if (pending) return <main className="page"><Skeleton label="Loading current identity…" /></main>;
  return identity ? <Outlet /> : <Navigate to="/login" replace />;
}

function AppShell() {
  const { identity, logout } = useAuth();
  return <>
    <a href="#main-content" className="sr-only focus:not-sr-only">Skip to content</a>
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-surface p-4">
      <div><strong>QualityTrack</strong><p className="text-sm text-muted">
        {identity?.display_name} · Plant timezone: {identity?.plant_zone}
      </p></div>
      <nav aria-label="Main navigation" className="flex flex-wrap items-center gap-4">
        <NavLink to="/defects">Defects</NavLink>
        <Button onClick={logout}>Sign out</Button>
      </nav>
    </header>
    <main id="main-content" className="page"><Outlet /></main>
  </>;
}

function FoundationPage({ title }: { title: string }) {
  return <><h1 tabIndex={-1}>{title}</h1>
    <EmptyState title="Not available in Batch 1">
      <p>This route is reserved for a later approved implementation batch. No records are loaded or changed.</p>
    </EmptyState></>;
}

function RecordEntry() {
  const { defectId } = useParams();
  return <Navigate to={`/defects/${encodeURIComponent(defectId ?? '')}/causes`} replace />;
}

function NotFoundPage() {
  return <><h1 tabIndex={-1}>Page not found</h1><p>This application route does not exist.</p></>;
}

// PUBLIC_INTERFACE
export function App() {
  /** Render only the approved foundation; business journeys remain unimplemented. */
  return <>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthBoundary />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/defects" replace />} />
          <Route path="/defects" element={<FoundationPage title="Defects" />} />
          <Route path="/defects/new" element={<FoundationPage title="Log defect" />} />
          <Route path="/defects/:defectId" element={<RecordEntry />} />
          <Route path="/defects/:defectId/causes" element={<FoundationPage title="Record cause" />} />
          <Route path="/defects/:defectId/investigation" element={<FoundationPage title="Start investigation" />} />
          <Route path="/defects/:defectId/actions" element={<FoundationPage title="Add corrective action" />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
    <RouteFocus />
  </>;
}
