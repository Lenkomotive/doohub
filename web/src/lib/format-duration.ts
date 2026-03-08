export function formatDuration(s: number): string {
  return s < 60
    ? `${Math.round(s)}s`
    : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}
