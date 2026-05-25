export function formatChannel(channel: string): string {
  return channel
    .split("_")
    .map((piece) => piece[0]?.toUpperCase() + piece.slice(1))
    .join(" ");
}

export function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatClockTime(value: number | Date): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(value instanceof Date ? value : new Date(value));
}

export function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
}
