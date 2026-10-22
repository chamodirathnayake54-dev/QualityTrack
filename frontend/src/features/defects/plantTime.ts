// PUBLIC_INTERFACE
export function plantTimeLabel(zone?: string): string {
  /** Present the signed-in plant zone as a readable place or UTC, not an internal zone code. */
  if (!zone || zone === 'UTC' || zone === 'Etc/UTC' || zone === 'Etc/GMT') return 'UTC';
  return zone.replace(/^Etc\//, '').replaceAll('_', ' ').split('/').join(' — ');
}
