import { Button } from "../../components/ui/Button";

export function WelcomeScreen({ onStart }: { onStart: () => void }) {
  return (
    <div className="text-center space-y-10">
      <div>
        <h1 className="text-5xl font-bold text-slate-900 mb-3">Welcome</h1>
        <p className="text-xl text-slate-600">City Service Center</p>
      </div>
      <p className="text-lg text-slate-500">
        General Enquiry &middot; Document Verification &middot; Application Submission &middot; Payment &middot;
        Technical Support
      </p>
      <Button size="xl" onClick={onStart} className="w-full sm:w-auto" aria-label="Get a token">
        Get a Token
      </Button>
    </div>
  );
}
