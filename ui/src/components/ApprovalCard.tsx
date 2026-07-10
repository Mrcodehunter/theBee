import type { ApprovalRequest } from "../types";

interface Props {
  request: ApprovalRequest;
  resolved: boolean;
  approved?: boolean;
  onDecide: (approved: boolean) => void;
}

export default function ApprovalCard({ request, resolved, approved, onDecide }: Props) {
  return (
    <div className="my-1 w-full max-w-2xl rounded-lg border border-amber-600/40 bg-amber-950/30 p-3 text-sm">
      <div className="mb-1 font-medium text-amber-300">
        {request.action === "write_file" ? "📝 File write requested" : "⚠️ Command execution requested"}
      </div>
      <div className="text-neutral-200">{request.summary}</div>
      {request.preview && (
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-neutral-900 p-2 font-mono text-xs text-neutral-300">
          {request.preview}
        </pre>
      )}
      {resolved ? (
        <div className={`mt-2 text-xs font-medium ${approved ? "text-emerald-400" : "text-red-400"}`}>
          {approved ? "Allowed" : "Denied"}
        </div>
      ) : (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => onDecide(true)}
            className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500"
          >
            Allow
          </button>
          <button
            onClick={() => onDecide(false)}
            className="rounded-md bg-neutral-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-600"
          >
            Deny
          </button>
        </div>
      )}
    </div>
  );
}
