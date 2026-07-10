interface Props {
  name: string;
  args: Record<string, unknown>;
  result: string | null;
}

export default function ToolCallChip({ name, args, result }: Props) {
  const argsPreview = Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");

  return (
    <details className="my-1 w-full max-w-2xl rounded-lg border border-neutral-700 bg-neutral-900/60 text-xs" open={result === null}>
      <summary className="cursor-pointer select-none px-3 py-2 font-mono text-neutral-300">
        🔧 {name}({argsPreview})
        {result === null && <span className="ml-2 animate-pulse text-neutral-500">running…</span>}
      </summary>
      {result !== null && (
        <pre className="max-h-56 overflow-auto whitespace-pre-wrap border-t border-neutral-800 px-3 py-2 font-mono text-neutral-400">
          {result}
        </pre>
      )}
    </details>
  );
}
