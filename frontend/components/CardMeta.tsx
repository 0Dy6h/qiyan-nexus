import type { CSSProperties } from "react";

import { getMetaRowStyle, getMetaTextStyle, joinMetaItems } from "../lib/ui/card-meta";

type CardMetaProps = {
  items: Array<string | null | undefined>;
};

export function CardMetaRow({ items }: CardMetaProps) {
  const joined = joinMetaItems(items);
  if (!joined) {
    return null;
  }
  return <p style={getMetaRowStyle() as CSSProperties}>{joined}</p>;
}

type CardBodyTextProps = {
  children: string;
};

export function CardBodyText({ children }: CardBodyTextProps) {
  return <p style={getMetaTextStyle() as CSSProperties}>{children}</p>;
}
