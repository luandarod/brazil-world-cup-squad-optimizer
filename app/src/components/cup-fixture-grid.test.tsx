// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CupFixtureGrid } from "./cup-fixture-grid";

describe("CupFixtureGrid", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the full TxLINE World Cup test grid", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      fixtures: [
        { fixtureId: 18237038, stage: "Semi-finals", kickoffUtc: "2026-07-14T19:00:00Z", home: "France", away: "Spain", live: true },
        { fixtureId: 18241006, stage: "Semi-finals", kickoffUtc: "2026-07-15T19:00:00Z", home: "England", away: "Argentina", live: true }
      ],
      liveCount: 2,
      total: 32
    })));

    render(<CupFixtureGrid />);

    await waitFor(() => expect(screen.getByText("France vs Spain")).toBeVisible());
    expect(screen.getByText(/2 jogos estão frescos/i)).toBeVisible();
    expect(screen.getByText(/#18241006/)).toBeVisible();
    expect(screen.getAllByText("TxLINE live")).toHaveLength(2);
  });
});
