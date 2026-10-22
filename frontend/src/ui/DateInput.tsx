import type { InputHTMLAttributes } from 'react';
import { TextInput } from './TextInput';

// PUBLIC_INTERFACE
export function DateInput(props: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>) {
  /** Keep date values as calendar strings rather than converting to instants. */
  return <TextInput {...props} type="date" />;
}
