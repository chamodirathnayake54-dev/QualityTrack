import type { TextareaHTMLAttributes } from 'react';

// PUBLIC_INTERFACE
export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  /** Render a resizable multiline input without domain validation. */
  return <textarea rows={4} {...props} className="control" />;
}
