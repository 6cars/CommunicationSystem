type Props = {
  label?: string;
};

export default function TypingIndicator({ label = "入力中..." }: Props) {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl rounded-bl-md bg-bubble-agent px-4 py-3 text-sm text-muted shadow-sm">
        {label}
      </div>
    </div>
  );
}
