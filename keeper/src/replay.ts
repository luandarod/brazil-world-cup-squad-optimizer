import type { KeeperEvent } from "./worker";

export type ReplayEvent = KeeperEvent & { mode: "REPLAY" };

export function replayEvent(event: KeeperEvent): ReplayEvent {
  if (!Number.isSafeInteger(event.fixtureId) || event.fixtureId <= 0) {
    throw new Error("Replay fixtureId must be a positive integer");
  }
  if (!Number.isSafeInteger(event.seq) || event.seq <= 0) {
    throw new Error("Replay seq must be a positive integer");
  }
  return { mode: "REPLAY", ...event };
}
