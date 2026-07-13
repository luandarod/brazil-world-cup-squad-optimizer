import { NextResponse } from "next/server";
import { txlineServerConfig } from "../../../../lib/txline-server";
import { WORLD_CUP_COMPETITION_ID } from "../../../../lib/world-cup-fixtures";

export async function GET() {
  const config = txlineServerConfig();
  if (!config.configured) {
    return NextResponse.json({ connected: false, missing: config.missing }, { status: 503 });
  }

  try {
    const response = await fetch(`${config.origin}/api/fixtures/snapshot?competitionId=${WORLD_CUP_COMPETITION_ID}`, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${config.jwt}`,
        "X-Api-Token": config.apiToken
      }
    });
    if (!response.ok) throw new Error(`TxLINE status ${response.status}`);
    return NextResponse.json({ connected: true, origin: config.origin });
  } catch {
    return NextResponse.json({ connected: false, error: "TxLINE request failed" }, { status: 502 });
  }
}
