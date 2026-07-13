import { NextResponse } from "next/server";
import { txlineServerConfig } from "../../../../lib/txline-server";
import { WORLD_CUP_COMPETITION_ID, mergeLiveFixtures } from "../../../../lib/world-cup-fixtures";

export async function GET() {
  const config = txlineServerConfig();
  if (!config.configured) {
    return NextResponse.json({ error: "TxLINE is not configured", missing: config.missing }, { status: 503 });
  }

  try {
    const response = await fetch(`${config.origin}/api/fixtures/snapshot?competitionId=${WORLD_CUP_COMPETITION_ID}`, {
      cache: "no-store",
      headers: { Accept: "application/json", Authorization: `Bearer ${config.jwt}`, "X-Api-Token": config.apiToken }
    });
    if (!response.ok) throw new Error("Upstream failure");

    const liveFixtures = await response.json();
    const fixtures = mergeLiveFixtures(liveFixtures);
    return NextResponse.json({
      competitionId: WORLD_CUP_COMPETITION_ID,
      fixtures,
      liveCount: Array.isArray(liveFixtures) ? liveFixtures.length : 0,
      total: fixtures.length
    });
  } catch {
    return NextResponse.json({ error: "TxLINE request failed" }, { status: 502 });
  }
}
