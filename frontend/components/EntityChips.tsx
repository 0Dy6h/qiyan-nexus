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
  border: "1px solid #14b8a6",
  background: "#f0fdfa",
  color: "#0d9488",
  fontSize: 13,
  fontWeight: 600,
  lineHeight: 1.4,
  textDecoration: "none",
};

const CHIP_KIND_STYLE = {
  color: "#64748b",
  fontWeight: 500,
};

const FALLBACK_CHIP_STYLE = {
  ...CHIP_STYLE,
  borderStyle: "dashed" as const,
  borderColor: "#cbd5e1",
  background: "white",
  color: "#64748b",
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
      <p style={{ color: "#94a3b8", margin: 0, marginTop: 8, fontSize: 13 }}>{emptyHint}</p>
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
