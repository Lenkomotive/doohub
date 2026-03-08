export function buildCron(preset: string, time: string, day?: number): string {
  const [h, m] = time.split(":").map(Number);
  switch (preset) {
    case "daily":
      return `${m} ${h} * * *`;
    case "weekly":
      return `${m} ${h} * * ${day}`;
    case "monthly":
      return `${m} ${h} ${day} * *`;
    default:
      return "";
  }
}

export function cronToHuman(cron: string): string {
  const parts = cron.split(" ");
  if (parts.length !== 5) return cron;
  const [min, hour, dom, , dow] = parts;
  const h = Number(hour);
  const m = Number(min);
  if (isNaN(h) || isNaN(m)) return cron;
  const timeStr = formatTime(h, m);

  if (dom === "*" && dow === "*") return `Every day at ${timeStr}`;
  if (dom === "*" && dow !== "*") {
    const dayName = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][Number(dow)];
    return dayName ? `Every ${dayName} at ${timeStr}` : cron;
  }
  if (dom !== "*" && dow === "*") {
    return `Monthly on the ${ordinal(Number(dom))} at ${timeStr}`;
  }
  return cron;
}

function formatTime(h: number, m: number): string {
  return new Date(2000, 0, 1, h, m).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export function formatNextRun(isoDate: string | null, timezone?: string): string {
  if (!isoDate) return "\u2014";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone,
  }).format(new Date(isoDate));
}
