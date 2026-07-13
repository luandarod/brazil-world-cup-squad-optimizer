import { TxlineHttpError, type StatValidationPayload } from "@vericup/txline";

import {
  decideMarketAction,
  eventKey,
  type KeeperAction,
  type MarketState
} from "./lifecycle";

export interface KeeperGateway {
  getMarket(fixtureId: number): Promise<{ state: MarketState; kickoff: number } | null>;
  lockMarket(fixtureId: number): Promise<void>;
  resolveMarket(fixtureId: number, seq: number, payload: StatValidationPayload): Promise<void>;
}

export interface ValidationProvider {
  proof(fixtureId: number, seq: number): Promise<StatValidationPayload>;
  renewJwt(): Promise<void>;
}

export interface KeeperEvent {
  fixtureId: number;
  seq: number;
  finalScore: boolean;
}

export class MarketKeeper {
  private readonly processed = new Set<string>();

  constructor(
    private readonly gateway: KeeperGateway,
    private readonly validation: ValidationProvider,
    private readonly capacity = 1_000
  ) {
    if (!Number.isInteger(capacity) || capacity < 1) {
      throw new Error("Keeper capacity must be a positive integer");
    }
  }

  async handle(event: KeeperEvent, now: number): Promise<KeeperAction> {
    const key = eventKey(event);
    if (this.processed.has(key)) return "NONE";

    const market = await this.gateway.getMarket(event.fixtureId);
    if (!market) return "NONE";

    let state = market.state;
    const firstAction = decideMarketAction({ ...market, now, finalScore: event.finalScore });
    if (firstAction === "LOCK") {
      await this.gateway.lockMarket(event.fixtureId);
      state = "LOCKED";
    }

    if (state === "LOCKED" && event.finalScore && now >= market.kickoff) {
      const proof = await this.proofWithRenewal(event.fixtureId, event.seq);
      await this.gateway.resolveMarket(event.fixtureId, event.seq, proof);
      this.remember(key);
      return "RESOLVE";
    }

    this.remember(key);
    return firstAction;
  }

  private async proofWithRenewal(fixtureId: number, seq: number): Promise<StatValidationPayload> {
    try {
      return await this.validation.proof(fixtureId, seq);
    } catch (error) {
      if (!(error instanceof TxlineHttpError) || error.status !== 401) throw error;
      await this.validation.renewJwt();
      return this.validation.proof(fixtureId, seq);
    }
  }

  private remember(key: string): void {
    if (this.processed.size >= this.capacity) {
      const oldest = this.processed.values().next().value;
      if (oldest !== undefined) this.processed.delete(oldest);
    }
    this.processed.add(key);
  }
}
