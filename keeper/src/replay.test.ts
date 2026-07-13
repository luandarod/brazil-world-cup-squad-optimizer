import { describe, expect, it } from "vitest";
import { replayEvent } from "./replay";

describe("verified replay", () => {
  it("labels historical events and preserves fixture sequence", () => {
    expect(replayEvent({ fixtureId: 18175981, seq: 991, finalScore: true })).toEqual({
      mode: "REPLAY",
      fixtureId: 18175981,
      seq: 991,
      finalScore: true
    });
  });

  it("rejects invalid identifiers before reaching the live keeper path", () => {
    expect(() => replayEvent({ fixtureId: -1, seq: 0, finalScore: true })).toThrow();
  });
});
