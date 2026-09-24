export function UncertaintyPanel({
  evidenceRequests,
  stopReason,
}: {
  evidenceRequests: string[];
  stopReason: string;
}) {
  return (
    <div className="bg-panel border border-border rounded mb-[18px]">
      <div className="px-[18px] py-3 border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
        Uncertainty &amp; additional evidence
      </div>
      <div className="px-[18px] py-4">
        {evidenceRequests.length === 0 ? (
          <div className="text-text-dim text-[13px] italic">
            No additional evidence was required to reach a defensible decision.
          </div>
        ) : (
          evidenceRequests.map((r, i) => (
            <div key={i} className="text-[13px] py-1.5 border-b border-border last:border-0">
              <span className="text-risk-medium font-mono">→ </span>
              {r}
            </div>
          ))
        )}
        <div className="text-text-muted text-[12px] mt-3 pt-3 border-t border-border">
          <span className="text-text-dim uppercase text-[10.5px] tracking-wide">Stop reason: </span>
          {stopReason}
        </div>
      </div>
    </div>
  );
}