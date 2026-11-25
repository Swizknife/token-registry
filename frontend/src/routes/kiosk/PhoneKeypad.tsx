import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "+", "0", "⌫"];

export function PhoneKeypad({
  value,
  onChange,
  onSubmit,
  onCancel,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const press = (key: string) => {
    if (key === "⌫") {
      onChange(value.slice(0, -1));
    } else if (value.length < 15) {
      onChange(value + key);
    }
  };

  const isValid = value.replace(/\D/g, "").length >= 10;

  return (
    <Card className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Enter your mobile number</h2>
        <p className="text-slate-500 mt-1">We'll send you a confirmation and queue updates by SMS.</p>
      </div>

      <div
        className="text-center text-4xl font-mono tracking-widest border-2 border-slate-200 rounded-xl py-4 min-h-[4.5rem]"
        aria-live="polite"
      >
        {value || <span className="text-slate-300">Enter number</span>}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {KEYS.map((key) => (
          <Button key={key} variant="secondary" size="xl" onClick={() => press(key)} aria-label={`Key ${key}`}>
            {key}
          </Button>
        ))}
      </div>

      <div className="flex gap-3">
        <Button variant="ghost" size="lg" onClick={onCancel} className="flex-1">
          Cancel
        </Button>
        <Button size="lg" onClick={onSubmit} disabled={!isValid} className="flex-1">
          Continue
        </Button>
      </div>
    </Card>
  );
}
