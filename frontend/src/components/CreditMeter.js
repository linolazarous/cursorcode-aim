import { Zap } from "lucide-react";

const PLAN_CREDITS = {
  starter: 10,
  standard: 75,
  pro: 150,
  premier: 600,
  ultra: 2000,
};

export default function CreditMeter({ credits, creditsUsed, plan }) {
  const maxCredits = PLAN_CREDITS[plan] || 10;
  const remaining = credits - creditsUsed;
  const percentage = Math.min((remaining / maxCredits) * 100, 100);
  const isLow = remaining < maxCredits * 0.15;
  const isCritical = remaining <= 0;

  return (
    <div
      className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border transition-all ${
        isCritical
          ? "border-red-500/40 bg-red-500/5"
          : isLow
          ? "border-amber-500/40 bg-amber-500/5"
          : "border-white/10 bg-white/[0.02]"
      }`}
      data-testid="credit-meter"
    >
      <div className={`p-1.5 rounded-full ${isCritical ? "bg-red-500/10" : isLow ? "bg-amber-500/10" : "bg-electric/10"}`}>
        <Zap className={`w-4 h-4 ${isCritical ? "text-red-400" : isLow ? "text-amber-400" : "text-electric"}`} />
      </div>

      <div className="flex-1 min-w-[120px]">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Credits</span>
          <span className="text-xs font-mono text-zinc-300" data-testid="credit-count">
            {remaining}/{maxCredits}
          </span>
        </div>
        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              isCritical ? "bg-red-500" : isLow ? "bg-amber-500" : "bg-electric"
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest whitespace-nowrap">
        {plan}
      </span>
    </div>
  );
}
