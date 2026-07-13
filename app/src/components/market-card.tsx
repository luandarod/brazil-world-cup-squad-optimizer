"use client";

import { useEffect, useRef, useState } from "react";

type Outcome = "HOME" | "DRAW" | "AWAY";

export function MarketCard({
  focusKey = 0,
  home,
  away,
  kickoff,
  pools
}: {
  focusKey?: number;
  home: string;
  away: string;
  kickoff: string;
  pools: [number, number, number];
}) {
  const [selected, setSelected] = useState<Outcome>("HOME");
  const [amount, setAmount] = useState("25");
  const [prompted, setPrompted] = useState(false);
  const [receipt, setReceipt] = useState<{ outcome: string; amount: string } | null>(null);
  const cardRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const outcomes: Array<{ code: Outcome; name: string; pool: number }> = [
    { code: "HOME", name: home, pool: pools[0] },
    { code: "DRAW", name: "Empate", pool: pools[1] },
    { code: "AWAY", name: away, pool: pools[2] }
  ];
  const selectedName = outcomes.find((outcome) => outcome.code === selected)?.name ?? home;

  useEffect(() => {
    if (focusKey === 0) return;
    cardRef.current?.scrollIntoView?.({ block: "center", behavior: "smooth" });
    inputRef.current?.focus();
    setPrompted(true);
    const timeout = window.setTimeout(() => setPrompted(false), 1400);
    return () => window.clearTimeout(timeout);
  }, [focusKey]);

  return (
    <section className={`market-card${prompted ? " is-prompted" : ""}`} aria-label={`${home} contra ${away}`} ref={cardRef}>
      <div className="fixture-meta">
        <span>SEMIFINAL · TXLINE #18237038</span>
        <time>{kickoff}</time>
      </div>
      <div className="teams">
        <strong>{home}</strong>
        <span>vs</span>
        <strong>{away}</strong>
      </div>
      <div className="outcomes">
        {outcomes.map((outcome) => (
          <button
            aria-pressed={selected === outcome.code}
            key={outcome.code}
            onClick={() => {
              setSelected(outcome.code);
              setReceipt(null);
            }}
            type="button"
          >
            <span>{outcome.name}</span>
            <b>{outcome.pool} PLAY</b>
          </button>
        ))}
      </div>
      <label className="amount-field">
        <span>POSIÇÃO</span>
        <input
          aria-label="Quantidade de PLAY"
          inputMode="numeric"
          onChange={(event) => {
            setAmount(event.target.value);
            setReceipt(null);
          }}
          ref={inputRef}
          value={amount}
        />
        <b>PLAY</b>
      </label>
      <button
        className="primary-action"
        disabled={!amount || Number(amount) <= 0}
        onClick={() => setReceipt({ outcome: selectedName, amount })}
        type="button"
      >
        {receipt ? "Palpite registrado" : `Registrar ${selectedName}`}
      </button>
      <p className="helper">Nenhuma carteira necessária. PLAY é pontuação virtual para a demo.</p>
      {receipt ? (
        <div className="guest-receipt" role="status">
          <b>Palpite registrado</b>
          <span>{receipt.outcome}, {receipt.amount} PLAY</span>
          <small>Próximo passo: aguardar o placar TxLINE para liquidação.</small>
        </div>
      ) : null}
    </section>
  );
}
