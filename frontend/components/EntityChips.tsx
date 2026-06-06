"use client";

import { useEffect, useState } from "react";

import {
  buildNetworkFocusHref,
  fetchNetworkEntities,
  getEntityKindLabel,
  type NetworkEntitiesLookup,
  type NetworkEntity,
} from "../lib/api/network-entities";

type EntityChipsProps = {
  ids: string[];
  emptyHint?: string;
};

const CHIP_CONTAINER_STYLE = {
  display: "flex",
  flexWrap: "wrap" as const,
  gap: 8,
  marginTop: 12,
};

const CHIP_STYLE = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "4px 10px",
  borderRadius: 999,
  borderWidth: 1,
  borderStyle: "solid" as const,
  borderColor: "rgba(45, 212, 191, 0.48)",
  background: "rgba(20, 184, 166, 0.14)",
  color: "var(--qiyan-teal-dark)",
  fontSize: 13,
  fontWeight: 600,
  lineHeight: 1.4,
  textDecoration: "none",
};

const CHIP_KIND_STYLE = {
  color: "var(--qiyan-muted-2)",
  fontWeight: 500,
};

const FALLBACK_CHIP_STYLE = {
  ...CHIP_STYLE,
  backdropFilter: "blur(10px) saturate(125%)",
  borderStyle: "dashed" as const,
  borderColor: "var(--qiyan-line)",
  background: "rgba(15, 23, 42, 0.32)",
  color: "var(--qiyan-muted-2)",
};

export default function EntityChips({ ids, emptyHint }: EntityChipsProps) {
  const [lookup, setLookup] = useState<NetworkEntitiesLookup | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchNetworkEntities()
      .then((result) => {
        if (!cancelled) {
          setLookup(result);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLookup({});
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ids || ids.length === 0) {
    return emptyHint ? (
      <p style={{ color: "var(--qiyan-muted-2)", margin: 0, marginTop: 8, fontSize: 13 }}>{emptyHint}</p>
    ) : null;
  }

  return (
    <div aria-label="相关网药实体" style={CHIP_CONTAINER_STYLE}>
      {ids.map((id) => {
        const entity: NetworkEntity | undefined = lookup ? lookup[id] : undefined;
        const href = buildNetworkFocusHref(id);
        if (!entity) {
          return (
            <a key={id} href={href} style={FALLBACK_CHIP_STYLE} title={id}>
              {id}
            </a>
          );
        }
        return (
          <a key={id} href={href} style={CHIP_STYLE} title={`跳转到 /network?focus=${id}`}>
            <span style={CHIP_KIND_STYLE}>{getEntityKindLabel(entity.kind)}</span>
            <span>{entity.name}</span>
          </a>
        );
      })}
    </div>
  );
}
