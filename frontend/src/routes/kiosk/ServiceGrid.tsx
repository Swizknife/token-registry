import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";

export function ServiceGrid({
  services,
  onSelect,
  onBack,
  submitting,
  error,
}: {
  services: string[];
  onSelect: (service: string) => void;
  onBack: () => void;
  submitting: boolean;
  error: string | null;
}) {
  return (
    <Card className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">What brings you in today?</h2>
        <p className="text-slate-500 mt-1">Select the service you need.</p>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-xl px-4 py-3" role="alert">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {services.map((service) => (
          <button
            key={service}
            disabled={submitting}
            onClick={() => onSelect(service)}
            className="min-h-[7rem] rounded-2xl border-2 border-slate-200 hover:border-brand-500 hover:bg-brand-50 transition-colors text-lg font-semibold text-slate-800 p-4 disabled:opacity-50 focus-visible:ring-4 focus-visible:ring-brand-300 outline-none"
          >
            {service}
          </button>
        ))}
      </div>

      <Button variant="ghost" size="lg" onClick={onBack} disabled={submitting}>
        Back
      </Button>
    </Card>
  );
}
