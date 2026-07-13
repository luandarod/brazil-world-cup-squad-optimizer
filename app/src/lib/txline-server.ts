export type TxlineServerConfig =
  | { configured: true; origin: string; jwt: string; apiToken: string }
  | { configured: false; missing: string[] };

export function txlineServerConfig(env: Record<string, string | undefined> = process.env): TxlineServerConfig {
  const origin = env.TXLINE_ORIGIN?.trim();
  const jwt = env.TXLINE_GUEST_JWT?.trim();
  const apiToken = env.TXLINE_API_TOKEN?.trim();
  const missing: string[] = [];
  if (!origin) missing.push("TXLINE_ORIGIN");
  if (!jwt) missing.push("TXLINE_GUEST_JWT");
  if (!apiToken) missing.push("TXLINE_API_TOKEN");

  if (missing.length > 0) return { configured: false, missing };
  return { configured: true, origin: origin!.replace(/\/+$/, ""), jwt: jwt!, apiToken: apiToken! };
}
