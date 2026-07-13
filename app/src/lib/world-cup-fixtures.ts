export type CupStage = "Group Stage" | "Round of 32" | "8th Finals" | "Quarter-finals" | "Semi-finals";

export interface CupFixture {
  fixtureId: number;
  stage: CupStage;
  kickoffUtc: string;
  home: string;
  away: string;
  score?: string;
  state?: string | number | null;
  live: boolean;
}

export const WORLD_CUP_COMPETITION_ID = 72;

export const WORLD_CUP_FIXTURES: CupFixture[] = [
  { fixtureId: 17588325, stage: "Group Stage", kickoffUtc: "2026-06-28T02:00:00Z", home: "Jordan", away: "Argentina", live: false },
  { fixtureId: 17588326, stage: "Group Stage", kickoffUtc: "2026-06-28T02:00:00Z", home: "Algeria", away: "Austria", live: false },
  { fixtureId: 18167317, stage: "Round of 32", kickoffUtc: "2026-06-28T19:00:00Z", home: "South Africa", away: "Canada", live: false },
  { fixtureId: 18172489, stage: "Round of 32", kickoffUtc: "2026-06-29T17:00:00Z", home: "Brazil", away: "Japan", live: false },
  { fixtureId: 18175983, stage: "Round of 32", kickoffUtc: "2026-06-29T20:30:00Z", home: "Germany", away: "Paraguay", live: false },
  { fixtureId: 18172260, stage: "Round of 32", kickoffUtc: "2026-06-30T01:00:00Z", home: "Netherlands", away: "Morocco", live: false },
  { fixtureId: 18175397, stage: "Round of 32", kickoffUtc: "2026-06-30T17:00:00Z", home: "Ivory Coast", away: "Norway", live: false },
  { fixtureId: 18175981, stage: "Round of 32", kickoffUtc: "2026-06-30T21:00:00Z", home: "France", away: "Sweden", live: false },
  { fixtureId: 18179759, stage: "Round of 32", kickoffUtc: "2026-07-01T01:00:00Z", home: "Mexico", away: "Ecuador", live: false },
  { fixtureId: 18179764, stage: "Round of 32", kickoffUtc: "2026-07-01T16:00:00Z", home: "England", away: "Congo DR", live: false },
  { fixtureId: 18179550, stage: "Round of 32", kickoffUtc: "2026-07-01T20:00:00Z", home: "Belgium", away: "Senegal", live: false },
  { fixtureId: 18172379, stage: "Round of 32", kickoffUtc: "2026-07-02T00:00:00Z", home: "USA", away: "Bosnia & Herzegovina", live: false },
  { fixtureId: 18179551, stage: "Round of 32", kickoffUtc: "2026-07-02T19:00:00Z", home: "Spain", away: "Austria", live: false },
  { fixtureId: 18179763, stage: "Round of 32", kickoffUtc: "2026-07-02T23:00:00Z", home: "Portugal", away: "Croatia", live: false },
  { fixtureId: 18179552, stage: "Round of 32", kickoffUtc: "2026-07-03T03:00:00Z", home: "Switzerland", away: "Algeria", live: false },
  { fixtureId: 18176123, stage: "Round of 32", kickoffUtc: "2026-07-03T18:00:00Z", home: "Australia", away: "Egypt", live: false },
  { fixtureId: 18175918, stage: "Round of 32", kickoffUtc: "2026-07-03T22:00:00Z", home: "Argentina", away: "Cape Verde", live: false },
  { fixtureId: 18179549, stage: "Round of 32", kickoffUtc: "2026-07-04T01:30:00Z", home: "Colombia", away: "Ghana", live: false },
  { fixtureId: 18185036, stage: "8th Finals", kickoffUtc: "2026-07-04T17:00:00Z", home: "Canada", away: "Morocco", live: false },
  { fixtureId: 18188721, stage: "8th Finals", kickoffUtc: "2026-07-04T21:03:00Z", home: "Paraguay", away: "France", live: false },
  { fixtureId: 18187298, stage: "8th Finals", kickoffUtc: "2026-07-05T20:00:00Z", home: "Brazil", away: "Norway", live: false },
  { fixtureId: 18192996, stage: "8th Finals", kickoffUtc: "2026-07-06T00:00:00Z", home: "Mexico", away: "England", live: false },
  { fixtureId: 18198205, stage: "8th Finals", kickoffUtc: "2026-07-06T19:00:00Z", home: "Portugal", away: "Spain", live: false },
  { fixtureId: 18193785, stage: "8th Finals", kickoffUtc: "2026-07-07T00:00:00Z", home: "USA", away: "Belgium", live: false },
  { fixtureId: 18202701, stage: "8th Finals", kickoffUtc: "2026-07-07T16:00:00Z", home: "Argentina", away: "Egypt", live: false },
  { fixtureId: 18202783, stage: "8th Finals", kickoffUtc: "2026-07-07T20:00:00Z", home: "Switzerland", away: "Colombia", live: false },
  { fixtureId: 18209181, stage: "Quarter-finals", kickoffUtc: "2026-07-09T20:00:00Z", home: "France", away: "Morocco", score: "2-0", live: false },
  { fixtureId: 18218149, stage: "Quarter-finals", kickoffUtc: "2026-07-10T19:00:00Z", home: "Spain", away: "Belgium", score: "2-1", live: false },
  { fixtureId: 18213979, stage: "Quarter-finals", kickoffUtc: "2026-07-11T21:00:00Z", home: "Norway", away: "England", score: "1-2", live: false },
  { fixtureId: 18222446, stage: "Quarter-finals", kickoffUtc: "2026-07-12T01:00:00Z", home: "Argentina", away: "Switzerland", score: "3-1", live: false },
  { fixtureId: 18237038, stage: "Semi-finals", kickoffUtc: "2026-07-14T19:00:00Z", home: "France", away: "Spain", live: false },
  { fixtureId: 18241006, stage: "Semi-finals", kickoffUtc: "2026-07-15T19:00:00Z", home: "England", away: "Argentina", live: false }
];

function fixtureState(value: unknown): string | number | null {
  if (typeof value === "string" || typeof value === "number") return value;
  return null;
}

export function mergeLiveFixtures(liveFixtures: unknown): CupFixture[] {
  if (!Array.isArray(liveFixtures)) return WORLD_CUP_FIXTURES;
  const byId = new Map(WORLD_CUP_FIXTURES.map((fixture) => [fixture.fixtureId, fixture]));

  for (const fixture of liveFixtures) {
    if (!fixture || typeof fixture !== "object") continue;
    const item = fixture as Record<string, unknown>;
    const fixtureId = Number(item.FixtureId);
    if (!Number.isSafeInteger(fixtureId)) continue;

    const current = byId.get(fixtureId);
    const home = String(item.Participant1 ?? current?.home ?? "TBD");
    const away = String(item.Participant2 ?? current?.away ?? "TBD");
    byId.set(fixtureId, {
      fixtureId,
      stage: current?.stage ?? "Semi-finals",
      kickoffUtc: typeof item.StartTime === "number" ? new Date(item.StartTime).toISOString() : current?.kickoffUtc ?? "",
      home,
      away,
      score: current?.score,
      state: fixtureState(item.GameState) ?? current?.state ?? null,
      live: true
    });
  }

  return [...byId.values()].sort((a, b) => a.kickoffUtc.localeCompare(b.kickoffUtc));
}
