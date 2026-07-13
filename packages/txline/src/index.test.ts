import { describe, expect, it, vi } from "vitest";

import {
  TxlineClient,
  bytes32,
  finalScoreSchema,
  mapValidationPayload,
  scoreOutcome
} from "./index";

const hash = Buffer.alloc(32, 7).toString("base64");

describe("finalScoreSchema", () => {
  it("normalises documented uppercase fixture and sequence fields", () => {
    const score = finalScoreSchema.parse({
      FixtureId: 18175981,
      Seq: 991,
      action: "game_finalised",
      statusId: 100,
      period: 100,
      participant1Score: 2,
      participant2Score: 1
    });

    expect(score).toEqual({
      fixtureId: 18175981,
      seq: 991,
      action: "game_finalised",
      statusId: 100,
      period: 100,
      home: 2,
      away: 1
    });
  });

  it("accepts lowercase aliases from mapped clients", () => {
    expect(finalScoreSchema.parse({
      fixtureId: 7,
      seq: 2,
      action: "game_finalised",
      statusId: 100,
      period: 100,
      home: 0,
      away: 0
    })).toMatchObject({ fixtureId: 7, seq: 2, home: 0, away: 0 });
  });

  it("rejects an in-play record", () => {
    expect(() => finalScoreSchema.parse({
      fixtureId: 1,
      seq: 3,
      action: "score_changed",
      statusId: 4,
      period: 4,
      home: 1,
      away: 0
    })).toThrow();
  });
});

describe("scoreOutcome", () => {
  it.each([
    [2, 1, "HOME"],
    [1, 1, "DRAW"],
    [0, 2, "AWAY"]
  ] as const)("maps %i-%i to %s", (home, away, outcome) => {
    expect(scoreOutcome(home, away)).toBe(outcome);
  });

  it("rejects negative scores", () => {
    expect(() => scoreOutcome(-1, 0)).toThrow("non-negative integers");
  });
});

describe("bytes32", () => {
  it("decodes base64, hex, arrays, and Uint8Array values", () => {
    const expected = Array(32).fill(7);
    expect(bytes32(hash)).toEqual(expected);
    expect(bytes32(`0x${Buffer.alloc(32, 7).toString("hex")}`)).toEqual(expected);
    expect(bytes32(expected)).toEqual(expected);
    expect(bytes32(Uint8Array.from(expected))).toEqual(expected);
  });

  it("rejects hashes that are not exactly 32 bytes", () => {
    expect(() => bytes32("AA==")).toThrow("Expected 32 bytes");
  });
});

describe("mapValidationPayload", () => {
  it("preserves requested stat order while mapping proof nodes", () => {
    const payload = mapValidationPayload({
      summary: {
        fixtureId: 42,
        updateStats: { updateCount: 3, minTimestamp: 1000, maxTimestamp: 2000 },
        eventStatsSubTreeRoot: hash
      },
      subTreeProof: [{ hash, isRightSibling: true }],
      mainTreeProof: [{ hash, isRightSibling: false }],
      eventStatRoot: hash,
      statsToProve: [
        { key: 1, value: 2, period: 100 },
        { key: 2, value: 1, period: 100 }
      ],
      statProofs: [
        [{ hash, isRightSibling: false }],
        [{ hash, isRightSibling: true }]
      ]
    });

    expect(payload.fixtureSummary.fixtureId).toBe(42);
    expect(payload.stats.map(({ stat }) => stat.key)).toEqual([1, 2]);
    expect(payload.stats[1]?.statProof[0]?.isRightSibling).toBe(true);
  });

  it("rejects mismatched stat and proof counts", () => {
    expect(() => mapValidationPayload({
      summary: {
        fixtureId: 42,
        updateStats: { updateCount: 1, minTimestamp: 1000, maxTimestamp: 1000 },
        eventStatsSubTreeRoot: hash
      },
      subTreeProof: [],
      mainTreeProof: [],
      eventStatRoot: hash,
      statsToProve: [{ key: 1, value: 0, period: 100 }],
      statProofs: []
    })).toThrow("one proof per stat");
  });
});

describe("TxlineClient", () => {
  it("requests a two-stat proof with both credentials", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ ok: true })));
    const client = new TxlineClient({
      origin: "https://txline-dev.txodds.com/",
      jwt: "guest-jwt",
      apiToken: "activated-token",
      fetch: fetchMock
    });

    await client.scoreValidation(42, 9, false);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, request] = fetchMock.mock.calls[0] ?? [];
    expect(String(url)).toBe("https://txline-dev.txodds.com/api/scores/stat-validation?fixtureId=42&seq=9&statKeys=1%2C2");
    expect(new Headers(request?.headers).get("Authorization")).toBe("Bearer guest-jwt");
    expect(new Headers(request?.headers).get("X-Api-Token")).toBe("activated-token");
  });

  it("throws a status-aware error for failed responses", async () => {
    const client = new TxlineClient({
      origin: "https://txline-dev.txodds.com",
      jwt: "guest-jwt",
      apiToken: "activated-token",
      fetch: vi.fn<typeof fetch>().mockResolvedValue(new Response("expired", { status: 401 }))
    });

    await expect(client.scoreSnapshot(42)).rejects.toMatchObject({ status: 401 });
  });
});
