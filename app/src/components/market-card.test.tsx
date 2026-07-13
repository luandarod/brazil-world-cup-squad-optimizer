// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarketCard } from "./market-card";

describe("MarketCard", () => {
  it("registers a walletless guest prediction", () => {
    render(<MarketCard home="França" away="Espanha" kickoff="14 JUL, 19:00 UTC" pools={[612, 488, 351]} />);

    expect(screen.getAllByText("França").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Espanha").length).toBeGreaterThan(0);

    const draw = screen.getByRole("button", { name: /empate/i });
    fireEvent.click(draw);

    expect(draw).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/nenhuma carteira necessária/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /registrar empate/i }));

    expect(screen.getByRole("status")).toHaveTextContent(/palpite registrado/i);
    expect(screen.getByRole("status")).toHaveTextContent(/empate/i);
    expect(screen.getByRole("status")).toHaveTextContent(/aguardar o placar TxLINE/i);
  });
});
