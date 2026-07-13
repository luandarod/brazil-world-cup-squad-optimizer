// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { HeroMarket } from "./hero-market";

describe("HeroMarket", () => {
  afterEach(cleanup);

  it("focuses the market amount when the hero CTA is clicked", () => {
    render(<HeroMarket />);

    fireEvent.click(screen.getByRole("button", { name: /testar mercado/i }));

    expect(screen.getByLabelText("Quantidade de PLAY")).toHaveFocus();
    expect(screen.getByLabelText("França contra Espanha")).toHaveClass("is-prompted");
  });

  it("focuses the market amount when the nav CTA is clicked", () => {
    render(<HeroMarket />);

    fireEvent.click(screen.getByRole("button", { name: /^testar$/i }));

    expect(screen.getByLabelText("Quantidade de PLAY")).toHaveFocus();
    expect(screen.getByLabelText("França contra Espanha")).toHaveClass("is-prompted");
  });
});
