"use client";

import { useEffect, useState } from "react";
import type { CupFixture } from "../lib/world-cup-fixtures";

type CupResponse = {
  fixtures: CupFixture[];
  liveCount: number;
  total: number;
};

function formatKickoff(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC"
  }).format(new Date(value));
}

export function CupFixtureGrid() {
  const [data, setData] = useState<CupResponse | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/txline/fixtures", { cache: "no-store" })
      .then((response) => response.json())
      .then((body) => {
        if (active) setData(body);
      })
      .catch(() => {
        if (active) setData(null);
      });
    return () => {
      active = false;
    };
  }, []);

  const fixtures = data?.fixtures ?? [];

  return (
    <section className="cup-section shell" id="copa">
      <div className="section-copy">
        <p className="eyebrow">COBERTURA TXLINE DA COPA</p>
        <h2>Toda partida confirmada vira mercado testável.</h2>
        <p>
          A grade combina o schedule oficial da TxLINE com o snapshot vivo da competição.
          Hoje {data?.liveCount ?? 0} jogos estão frescos no endpoint e {data?.total ?? fixtures.length} ficam disponíveis para teste/replay.
        </p>
      </div>
      <div className="fixture-grid" aria-label="Jogos da Copa disponíveis para teste">
        {fixtures.map((fixture) => (
          <article className="fixture-row" key={fixture.fixtureId}>
            <span>{fixture.stage}</span>
            <b>{fixture.home} vs {fixture.away}</b>
            <small>{formatKickoff(fixture.kickoffUtc)} UTC · #{fixture.fixtureId}</small>
            <em>{fixture.live ? "TxLINE live" : fixture.score ? `Final ${fixture.score}` : "Replay pronto"}</em>
          </article>
        ))}
      </div>
    </section>
  );
}
