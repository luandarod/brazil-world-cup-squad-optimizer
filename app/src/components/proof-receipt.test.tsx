// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProofReceipt } from "./proof-receipt";

describe("ProofReceipt", () => {
  it("renders the source, score and immutable receipt", () => {
    render(<ProofReceipt fixtureId={18175981} score="2 - 1" slot={421337991} hash="a19c72f6e8b42291147f9a9bdac33f08" />);
    expect(screen.getByText("TxLINE validateStatV2")).toBeInTheDocument();
    expect(screen.getByText("DEMO LOCAL")).toBeInTheDocument();
    expect(screen.getByText("2 - 1")).toBeInTheDocument();
    expect(screen.getByText(/a19c72f6/)).toBeInTheDocument();
    expect(screen.getByText("421337991")).toBeInTheDocument();
  });
});
