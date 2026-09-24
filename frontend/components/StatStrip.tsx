import { CaseFull } from "@/lib/types";

const RISK_TEXT_COLOR: Record<string, string> = {
  high: "#C9564A",
  medium: "#C99A3D",
  low: "#4A9C7C",
};

function fmtMoney(n: number) {
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function StatStrip({ data }: { data: CaseFull }) {
  const { case: c, sar } = data;
  const stats = [
    { label: "Risk level", value: c.risk_level, color: RISK_TEXT_COLOR[c.risk_level] },
    { label: "Confidence", value: `${(c.confidence * 100).toFixed(0)}%` },
    { label: "Exposure", value: fmtMoney(c.exposure_amount) },
    { label: "SAR required", value: sar.required ? "Yes" : "No" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border border border-border mb-6">
      {stats.map((s) => (
        <div key={s.label} className="bg-panel px-4 py-3.5">
          <div className="text-[11px] text-text-dim uppercase tracking-wide mb-1.5">{s.label}</div>
          <div className="font-mono text-[17px] font-semibold" style={{ color: s.color }}>
            {s.value}
          </div>
        </div>
      ))}
    </div>
  );
}