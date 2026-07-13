import { describe, expect, it, vi } from "vitest";

import { TxlineHttpError, type StatValidationPayload } from "@vericup/txline";

import {
  decideMarketAction,
  eventKey,
  reconnectDelay
} from "./lifecycle";
import { MarketKeeper, type KeeperGateway, type ValidationProvider } from "./worker";

const payload = {} as StatValidationPayload;

describe("keeper lifecycle", () => {
  it("locks an open market at kickoff", () => {
    expect(decideMarketAction({ state: "OPEN", kickoff: 100, now: 100 })).toBe("LOCK");
  });

  it("resolves only a locked market with a final score", () => {
    expect(decideMarketAction({
      state: "LOCKED",
      kickoff: 100,
      now: 110,
      finalScore: true
    })).toBe("RESOLVE");
    expect(decideMarketAction({
      state: "OPEN",
      kickoff: 100,
      now: 110,
      finalScore: true
    })).toBe("LOCK");
  });

  it("does nothing before kickoff or after resolution", () => {
    expect(decideMarketAction({ state: "OPEN", kickoff: 100, now: 99 })).toBe("NONE");
    expect(decideMarketAction({ state: "RESOLVED", kickoff: 100, now: 200, finalScore: true })).toBe("NONE");
  });

  it("deduplicates by fixture and sequence", () => {
    expect(eventKey({ fixtureId: 42, seq: 7 })).toBe("42:7");
  });

  it("caps reconnect delay at thirty seconds", () => {
    expect(reconnectDelay(20)).toBe(30_000);
  });

  it("rejects negative reconnect attempts", () => {
    expect(() => reconnectDelay(-1)).toThrow("non-negative integer");
  });
});

function dependencies(overrides: Partial<{
  gateway: KeeperGateway;
  validation: ValidationProvider;
}> = {}) {
  const gateway: KeeperGateway = overrides.gateway ?? {
    getMarket: vi.fn().mockResolvedValue({ state: "OPEN", kickoff: 100 }),
    lockMarket: vi.fn().mockResolvedValue(undefined),
    resolveMarket: vi.fn().mockResolvedValue(undefined)
  };
  const validation: ValidationProvider = overrides.validation ?? {
    proof: vi.fn().mockResolvedValue(payload),
    renewJwt: vi.fn().mockResolvedValue(undefined)
  };
  return { gateway, validation };
}

describe("MarketKeeper", () => {
  it("locks then resolves a final event for an open market", async () => {
    const { gateway, validation } = dependencies();
    const keeper = new MarketKeeper(gateway, validation);

    await expect(keeper.handle({ fixtureId: 42, seq: 7, finalScore: true }, 110)).resolves.toBe("RESOLVE");

    expect(gateway.lockMarket).toHaveBeenCalledWith(42);
    expect(validation.proof).toHaveBeenCalledWith(42, 7);
    expect(gateway.resolveMarket).toHaveBeenCalledWith(42, 7, payload);
  });

  it("ignores an event only after its transaction succeeds", async () => {
    const resolveMarket = vi.fn()
      .mockRejectedValueOnce(new Error("RPC unavailable"))
      .mockResolvedValueOnce(undefined);
    const { gateway, validation } = dependencies({
      gateway: {
        getMarket: vi.fn().mockResolvedValue({ state: "LOCKED", kickoff: 100 }),
        lockMarket: vi.fn(),
        resolveMarket
      }
    });
    const keeper = new MarketKeeper(gateway, validation);
    const event = { fixtureId: 42, seq: 7, finalScore: true };

    await expect(keeper.handle(event, 110)).rejects.toThrow("RPC unavailable");
    await expect(keeper.handle(event, 110)).resolves.toBe("RESOLVE");
    await expect(keeper.handle(event, 110)).resolves.toBe("NONE");
    expect(resolveMarket).toHaveBeenCalledTimes(2);
  });

  it("renews an expired guest JWT and retries the proof once", async () => {
    const proof = vi.fn()
      .mockRejectedValueOnce(new TxlineHttpError(401, "expired"))
      .mockResolvedValueOnce(payload);
    const renewJwt = vi.fn().mockResolvedValue(undefined);
    const { gateway, validation } = dependencies({
      gateway: {
        getMarket: vi.fn().mockResolvedValue({ state: "LOCKED", kickoff: 100 }),
        lockMarket: vi.fn(),
        resolveMarket: vi.fn()
      },
      validation: { proof, renewJwt }
    });

    await new MarketKeeper(gateway, validation).handle({ fixtureId: 42, seq: 7, finalScore: true }, 110);

    expect(renewJwt).toHaveBeenCalledOnce();
    expect(proof).toHaveBeenCalledTimes(2);
  });
});
