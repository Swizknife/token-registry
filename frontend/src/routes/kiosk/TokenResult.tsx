import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { TokenCreateResponse } from "../../lib/api";

export function TokenResult({ token, onDone }: { token: TokenCreateResponse; onDone: () => void }) {
  return (
    <Card className="text-center space-y-6" aria-live="assertive">
      <p className="text-slate-500 text-lg">Your token number is</p>
      <div className="text-7xl font-black text-brand-700 tracking-wide">{token.token_number}</div>
      <div className="space-y-1">
        <p className="text-xl text-slate-700">{token.service_category}</p>
        <p className="text-base text-slate-500 capitalize">Status: {token.status}</p>
        {token.estimated_wait_time != null && (
          <p className="text-base text-slate-500">
            Estimated wait: ~{Math.max(1, Math.round(token.estimated_wait_time / 60))} min
          </p>
        )}
      </div>
      <p className="text-slate-400 text-sm">A confirmation SMS has been sent to your phone.</p>
      <Button size="lg" onClick={onDone}>
        Done
      </Button>
    </Card>
  );
}
