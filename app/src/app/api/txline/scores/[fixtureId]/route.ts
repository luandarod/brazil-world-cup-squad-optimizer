import { TxlineClient } from "@vericup/txline";
import { NextResponse } from "next/server";
import { txlineServerConfig } from "../../../../../lib/txline-server";

export async function GET(_request: Request, context: { params: Promise<{ fixtureId: string }> }) {
  const { fixtureId } = await context.params;
  const id = Number(fixtureId);
  if (!Number.isSafeInteger(id) || id <= 0) return NextResponse.json({ error: "Invalid fixture" }, { status: 400 });
  const config = txlineServerConfig();
  if (!config.configured) {
    return NextResponse.json({ error: "TxLINE is not configured", missing: config.missing }, { status: 503 });
  }
  try {
    const client = new TxlineClient({ origin: config.origin, jwt: config.jwt, apiToken: config.apiToken });
    return NextResponse.json(await client.scoreSnapshot(id));
  } catch {
    return NextResponse.json({ error: "TxLINE request failed" }, { status: 502 });
  }
}
