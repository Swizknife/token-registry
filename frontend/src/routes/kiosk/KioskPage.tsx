import { useCallback, useEffect, useState } from "react";

import { ApiError, createToken, getServices, TokenCreateResponse } from "../../lib/api";
import { PhoneKeypad } from "./PhoneKeypad";
import { ServiceGrid } from "./ServiceGrid";
import { TokenResult } from "./TokenResult";
import { WelcomeScreen } from "./WelcomeScreen";

type Step = "welcome" | "phone" | "service" | "token";

const RESET_SECONDS = Number(import.meta.env.VITE_KIOSK_RESET_SECONDS ?? 20);

export default function KioskPage() {
  const [step, setStep] = useState<Step>("welcome");
  const [phone, setPhone] = useState("");
  const [services, setServices] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [token, setToken] = useState<TokenCreateResponse | null>(null);

  useEffect(() => {
    getServices()
      .then(setServices)
      .catch(() => setServices([]));
  }, []);

  const reset = useCallback(() => {
    setStep("welcome");
    setPhone("");
    setToken(null);
    setError(null);
  }, []);

  // Auto-return to welcome after a token is issued, or after an error.
  useEffect(() => {
    if (step !== "token") return;
    const timer = setTimeout(reset, RESET_SECONDS * 1000);
    return () => clearTimeout(timer);
  }, [step, reset]);

  const handleServiceSelect = async (service: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await createToken(phone, service);
      setToken(result);
      setStep("token");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="h-screen w-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-3xl">
        {step === "welcome" && (
          <WelcomeScreen onStart={() => setStep("phone")} />
        )}
        {step === "phone" && (
          <PhoneKeypad
            value={phone}
            onChange={setPhone}
            onCancel={reset}
            onSubmit={() => setStep("service")}
          />
        )}
        {step === "service" && (
          <ServiceGrid
            services={services}
            onSelect={handleServiceSelect}
            onBack={() => setStep("phone")}
            submitting={submitting}
            error={error}
          />
        )}
        {step === "token" && token && <TokenResult token={token} onDone={reset} />}
      </div>
    </div>
  );
}
