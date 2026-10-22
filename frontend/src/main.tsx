import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiClient } from './api/client';
import { AuthProvider } from './features/auth/AuthProvider';
import { App } from './app/App';
import './styles/tokens.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root')!);
try {
  // Request VITE_API_BASE_URL from the environment owner; frontend values are public.
  const client = new ApiClient(import.meta.env.VITE_API_BASE_URL ?? '');
  root.render(<React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider client={client}><App /></AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>);
} catch {
  root.render(<main className="page"><h1>Configuration required</h1>
    <p role="alert">QualityTrack is not ready yet. Please ask your support team to finish setting it up.</p>
  </main>);
}
