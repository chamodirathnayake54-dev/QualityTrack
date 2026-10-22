import type { InputHTMLAttributes } from 'react';

// PUBLIC_INTERFACE
export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  /** Render a native input, preserving accessible and form attributes. */
  return <input {...props} className="control" />;
}
