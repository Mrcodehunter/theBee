interface Props {
  role: "user" | "assistant";
  content: string;
}

export default function MessageBubble({ role, content }: Props) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-2xl whitespace-pre-wrap rounded-2xl bg-blue-600 px-4 py-2.5 text-sm text-white">
          {content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-2xl whitespace-pre-wrap rounded-2xl bg-neutral-800 px-4 py-2.5 text-sm text-neutral-100">
        {content}
      </div>
    </div>
  );
}
