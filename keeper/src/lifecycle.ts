export type MarketState = "OPEN" | "LOCKED" | "RESOLVED";
export type KeeperAction = "NONE" | "LOCK" | "RESOLVE";

export function decideMarketAction(input: {
  state: MarketState;
  kickoff: number;
  now: number;
  finalScore?: boolean;
}): KeeperAction {
  if (input.state === "RESOLVED" || input.now < input.kickoff) return "NONE";
  if (input.state === "OPEN") return "LOCK";
  return input.finalScore ? "RESOLVE" : "NONE";
}

export function eventKey(event: { fixtureId: number; seq: number }): string {
  if (!Number.isInteger(event.fixtureId) || event.fixtureId < 1 || !Number.isInteger(event.seq) || event.seq < 1) {
    throw new Error("Fixture and sequence must be positive integers");
  }
  return `${event.fixtureId}:${event.seq}`;
}

export function reconnectDelay(attempt: number): number {
  if (!Number.isInteger(attempt) || attempt < 0) {
    throw new Error("Reconnect attempt must be a non-negative integer");
  }
  return Math.min(30_000, 1_000 * 2 ** attempt);
}
