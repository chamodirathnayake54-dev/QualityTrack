import { useState, type FormEvent } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { Alert, Button, ErrorSummary, Field, TextInput } from '../../ui';
import { useAuth } from './AuthProvider';

// PUBLIC_INTERFACE
export function LoginPage() {
  /** Sign in with unchanged credential text, then enter the authenticated shell. */
  const { identity, pending, login } = useAuth();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');

  const from = location.state?.from;
  const destination = typeof from === 'string' && /^\/defects(?:\/|\?|$)/.test(from) ? from : '/defects';
  if (identity) return <Navigate to={destination} replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    const errors: Record<string, string> = {};
    if (!username.trim()) errors.username = 'Enter your username.';
    if (!password) errors.password = 'Enter your password.';
    setFields(errors);
    setMessage('');
    if (Object.keys(errors).length) return;
    try {
      await login(username, password);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') return;
      setFields(error instanceof ApiError ? error.problem.field_errors ?? {} : {});
      setMessage(error instanceof ApiError ? error.message : 'Sign-in could not complete. Try again.');
    } finally {
      setPassword('');
    }
  };

  return <main className="page">
    <h1 tabIndex={-1}>Sign in to QualityTrack</h1>
    <p className="text-muted">For your security you are signed out if you refresh this page.</p>
    {Object.keys(fields).length > 0 &&
      <ErrorSummary errors={Object.entries(fields).map(([key, value]) => ({ label: `${key}: ${value}` }))} />}
    {message && <Alert tone="danger">{message}</Alert>}
    <form onSubmit={submit} noValidate className="space-y-6 rounded-control border border-border bg-surface p-6">
      <Field label="Username" error={fields.username}>{(props) =>
        <TextInput {...props} name="username" autoComplete="username" autoCapitalize="none" autoCorrect="off" spellCheck={false} value={username}
          disabled={pending} onChange={(event) => setUsername(event.target.value)} />}</Field>
      <Field label="Password" error={fields.password}>{(props) =>
        <TextInput {...props} name="password" type="password" autoComplete="current-password" value={password}
          disabled={pending} onChange={(event) => setPassword(event.target.value)} />}</Field>
      <Button type="submit" pending={pending}>{pending ? 'Signing in…' : 'Sign in'}</Button>
    </form>
  </main>;
}
