import { z } from "zod";

export type Outcome = "HOME" | "DRAW" | "AWAY";

export interface FinalScore {
  fixtureId: number;
  seq: number;
  action: "game_finalised";
  statusId: 100;
  period: 100;
  home: number;
  away: number;
}

export interface ProofNode {
  hash: number[];
  isRightSibling: boolean;
}

export interface ScoreStat {
  key: number;
  value: number;
  period: number;
}

export interface StatValidationPayload {
  ts: number;
  fixtureSummary: {
    fixtureId: number;
    updateStats: {
      updateCount: number;
      minTimestamp: number;
      maxTimestamp: number;
    };
    eventsSubTreeRoot: number[];
  };
  fixtureProof: ProofNode[];
  mainTreeProof: ProofNode[];
  eventStatRoot: number[];
  stats: Array<{ stat: ScoreStat; statProof: ProofNode[] }>;
}

const nonNegativeInteger = z.number().int().nonnegative();

const rawFinalScoreSchema = z.object({
  FixtureId: z.number().int().positive().optional(),
  fixtureId: z.number().int().positive().optional(),
  Seq: z.number().int().positive().optional(),
  seq: z.number().int().positive().optional(),
  action: z.literal("game_finalised"),
  statusId: z.literal(100),
  period: z.literal(100),
  participant1Score: nonNegativeInteger.optional(),
  participant2Score: nonNegativeInteger.optional(),
  home: nonNegativeInteger.optional(),
  away: nonNegativeInteger.optional()
}).superRefine((value, context) => {
  if (value.FixtureId === undefined && value.fixtureId === undefined) {
    context.addIssue({ code: "custom", message: "fixtureId is required" });
  }
  if (value.Seq === undefined && value.seq === undefined) {
    context.addIssue({ code: "custom", message: "seq is required" });
  }
  if (value.participant1Score === undefined && value.home === undefined) {
    context.addIssue({ code: "custom", message: "home score is required" });
  }
  if (value.participant2Score === undefined && value.away === undefined) {
    context.addIssue({ code: "custom", message: "away score is required" });
  }
});

export const finalScoreSchema = rawFinalScoreSchema.transform((value): FinalScore => ({
  fixtureId: value.fixtureId ?? value.FixtureId!,
  seq: value.seq ?? value.Seq!,
  action: value.action,
  statusId: value.statusId,
  period: value.period,
  home: value.home ?? value.participant1Score!,
  away: value.away ?? value.participant2Score!
}));

export function scoreOutcome(home: number, away: number): Outcome {
  if (!Number.isInteger(home) || !Number.isInteger(away) || home < 0 || away < 0) {
    throw new Error("Scores must be non-negative integers");
  }
  if (home === away) return "DRAW";
  return home > away ? "HOME" : "AWAY";
}

export function bytes32(value: string | number[] | Uint8Array): number[] {
  let bytes: Uint8Array;
  if (typeof value === "string") {
    if (value.startsWith("0x")) {
      const hex = value.slice(2);
      if (!/^[\da-fA-F]+$/.test(hex) || hex.length % 2 !== 0) {
        throw new Error("Invalid hex hash");
      }
      bytes = Uint8Array.from(hex.match(/.{2}/g) ?? [], (part) => Number.parseInt(part, 16));
    } else {
      bytes = Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
    }
  } else {
    bytes = Uint8Array.from(value);
  }

  if (bytes.length !== 32) {
    throw new Error(`Expected 32 bytes, received ${bytes.length}`);
  }
  return Array.from(bytes);
}

const proofNodeSchema = z.object({
  hash: z.union([z.string(), z.array(z.number().int().min(0).max(255)), z.instanceof(Uint8Array)]),
  isRightSibling: z.boolean()
});

const validationSchema = z.object({
  summary: z.object({
    fixtureId: z.number().int().positive(),
    updateStats: z.object({
      updateCount: z.number().int().nonnegative(),
      minTimestamp: z.number().int().nonnegative(),
      maxTimestamp: z.number().int().nonnegative()
    }),
    eventStatsSubTreeRoot: z.union([z.string(), z.array(z.number()), z.instanceof(Uint8Array)])
  }),
  subTreeProof: z.array(proofNodeSchema),
  mainTreeProof: z.array(proofNodeSchema),
  eventStatRoot: z.union([z.string(), z.array(z.number()), z.instanceof(Uint8Array)]),
  statsToProve: z.array(z.object({
    key: z.number().int().nonnegative(),
    value: z.number().int(),
    period: z.number().int()
  })),
  statProofs: z.array(z.array(proofNodeSchema))
});

function mapProof(nodes: z.infer<typeof proofNodeSchema>[]): ProofNode[] {
  return nodes.map((node) => ({
    hash: bytes32(node.hash),
    isRightSibling: node.isRightSibling
  }));
}

export function mapValidationPayload(value: unknown): StatValidationPayload {
  const validation = validationSchema.parse(value);
  if (validation.statsToProve.length !== validation.statProofs.length) {
    throw new Error("TxLINE validation requires one proof per stat");
  }

  return {
    ts: validation.summary.updateStats.minTimestamp,
    fixtureSummary: {
      fixtureId: validation.summary.fixtureId,
      updateStats: validation.summary.updateStats,
      eventsSubTreeRoot: bytes32(validation.summary.eventStatsSubTreeRoot)
    },
    fixtureProof: mapProof(validation.subTreeProof),
    mainTreeProof: mapProof(validation.mainTreeProof),
    eventStatRoot: bytes32(validation.eventStatRoot),
    stats: validation.statsToProve.map((stat, index) => ({
      stat,
      statProof: mapProof(validation.statProofs[index]!)
    }))
  };
}

export class TxlineHttpError extends Error {
  constructor(public readonly status: number, body: string) {
    super(`TxLINE request failed with ${status}: ${body}`);
    this.name = "TxlineHttpError";
  }
}

export class TxlineClient {
  private readonly origin: string;
  private readonly fetch: typeof fetch;

  constructor(private readonly config: {
    origin: string;
    jwt: string;
    apiToken: string;
    fetch?: typeof fetch;
  }) {
    this.origin = config.origin.replace(/\/$/, "");
    this.fetch = config.fetch ?? globalThis.fetch;
  }

  scoreSnapshot(fixtureId: number): Promise<unknown> {
    return this.request(`/api/scores/snapshot/${fixtureId}?asOf=${Date.now()}`);
  }

  async scoreValidation(
    fixtureId: number,
    seq: number,
    mapPayload = true
  ): Promise<StatValidationPayload | unknown> {
    const query = new URLSearchParams({
      fixtureId: String(fixtureId),
      seq: String(seq),
      statKeys: "1,2"
    });
    const response = await this.request(`/api/scores/stat-validation?${query}`);
    return mapPayload ? mapValidationPayload(response) : response;
  }

  private async request(path: string): Promise<unknown> {
    const response = await this.fetch(`${this.origin}${path}`, {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${this.config.jwt}`,
        "X-Api-Token": this.config.apiToken
      }
    });
    if (!response.ok) {
      throw new TxlineHttpError(response.status, await response.text());
    }
    return response.json();
  }
}
