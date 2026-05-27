import type { VQEIteration } from "../api/client";

interface Props {
  iterations: VQEIteration[];
}

// Plain SVG line chart — keeps the bundle small and avoids a charting
// library dependency for what is a single-purpose plot.
export function EnergyChart({ iterations }: Props) {
  const width = 600;
  const height = 240;
  const padding = { top: 12, right: 16, bottom: 32, left: 56 };

  if (iterations.length === 0) {
    return (
      <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Empty chart">
        <text
          x={width / 2}
          y={height / 2}
          textAnchor="middle"
          fill="#555"
        >
          Energy trace will appear here once iterations start.
        </text>
      </svg>
    );
  }

  const energies = iterations.map((it) => it.energy);
  const minE = Math.min(...energies);
  const maxE = Math.max(...energies);
  const eRange = maxE - minE || 1;
  const maxIter = iterations.length;

  const xFor = (i: number) =>
    padding.left + ((i - 1) / Math.max(maxIter - 1, 1)) * (width - padding.left - padding.right);
  const yFor = (energy: number) =>
    padding.top + (1 - (energy - minE) / eRange) * (height - padding.top - padding.bottom);

  const pathD = iterations
    .map((it, idx) => `${idx === 0 ? "M" : "L"} ${xFor(it.iteration)} ${yFor(it.energy)}`)
    .join(" ");

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Energy vs iteration, ${iterations.length} points, current ${energies[energies.length - 1].toFixed(6)} Hartree`}
    >
      <line
        className="axis"
        x1={padding.left}
        y1={height - padding.bottom}
        x2={width - padding.right}
        y2={height - padding.bottom}
      />
      <line
        className="axis"
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={height - padding.bottom}
      />
      <text x={padding.left} y={padding.top - 2} fontSize="11" fill="#555">
        {maxE.toFixed(4)}
      </text>
      <text x={padding.left} y={height - padding.bottom + 12} fontSize="11" fill="#555">
        {minE.toFixed(4)}
      </text>
      <text
        x={width / 2}
        y={height - 6}
        textAnchor="middle"
        fontSize="11"
        fill="#555"
      >
        iteration (1 – {maxIter})
      </text>
      <text
        x={12}
        y={height / 2}
        transform={`rotate(-90 12 ${height / 2})`}
        fontSize="11"
        fill="#555"
      >
        energy (Hartree)
      </text>
      <path className="trace" d={pathD} />
      {iterations.map((it) => (
        <circle
          key={it.iteration}
          className="point"
          cx={xFor(it.iteration)}
          cy={yFor(it.energy)}
          r={3}
        />
      ))}
    </svg>
  );
}
