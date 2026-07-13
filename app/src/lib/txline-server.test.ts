import { describe, expect, it } from "vitest";
import { txlineServerConfig } from "./txline-server";

describe("txlineServerConfig", () => {
  it("requires all server-only TxLINE credentials", () => {
    expect(txlineServerConfig({ TXLINE_ORIGIN: "https://txline-dev.txodds.com" })).toEqual({
      configured: false,
      missing: ["TXLINE_GUEST_JWT", "TXLINE_API_TOKEN"]
    });
  });

  it("normalizes configured credentials", () => {
    expect(txlineServerConfig({
      TXLINE_ORIGIN: " https://txline-dev.txodds.com/ ",
      TXLINE_GUEST_JWT: " jwt ",
      TXLINE_API_TOKEN: " token "
    })).toEqual({
      configured: true,
      origin: "https://txline-dev.txodds.com",
      jwt: "jwt",
      apiToken: "token"
    });
  });
});
