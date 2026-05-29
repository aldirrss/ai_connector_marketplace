import type { TransportType } from "@/lib/types";
import { TRANSPORT_LABEL, TRANSPORT_STYLE } from "@/lib/labels";

export function TransportBadge({ transport }: { transport: TransportType }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TRANSPORT_STYLE[transport]}`}
    >
      {TRANSPORT_LABEL[transport]}
    </span>
  );
}
