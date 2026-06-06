import {
  getLiteratureDataSourceBanner,
  type LiteratureDataSourceView,
} from "../lib/api/literature";

type Props = { view: LiteratureDataSourceView };

type ToneStyle = {
  background: string;
  border: string;
  badgeBackground: string;
  badgeColor: string;
  titleColor: string;
  bodyColor: string;
};

const TONE_STYLES: Record<ReturnType<typeof getLiteratureDataSourceBanner>["tone"], ToneStyle> = {
  info: {
    background: "rgba(7, 33, 29, 0.72)",
    border: "1px solid rgba(45, 212, 191, 0.42)",
    badgeBackground: "rgba(20, 184, 166, 0.18)",
    badgeColor: "#99f6e4",
    titleColor: "#99f6e4",
    bodyColor: "#ccfbf1",
  },
  live: {
    background: "rgba(12, 25, 54, 0.78)",
    border: "1px solid rgba(96, 165, 250, 0.42)",
    badgeBackground: "rgba(37, 99, 235, 0.2)",
    badgeColor: "#bfdbfe",
    titleColor: "#bfdbfe",
    bodyColor: "#dbeafe",
  },
  sample: {
    background: "rgba(36, 24, 5, 0.72)",
    border: "1px solid rgba(245, 158, 11, 0.44)",
    badgeBackground: "rgba(245, 158, 11, 0.18)",
    badgeColor: "#fde68a",
    titleColor: "#fde68a",
    bodyColor: "#f9d99a",
  },
  upload: {
    background: "rgba(34, 20, 63, 0.72)",
    border: "1px solid rgba(167, 139, 250, 0.44)",
    badgeBackground: "rgba(139, 92, 246, 0.2)",
    badgeColor: "#ddd6fe",
    titleColor: "#ddd6fe",
    bodyColor: "#ede9fe",
  },
};

export default function LiteratureDataSourceBanner({ view }: Props) {
  const banner = getLiteratureDataSourceBanner(view);
  const style = TONE_STYLES[banner.tone];

  return (
    <section
      role="note"
      aria-label="数据来源说明"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        padding: 16,
        border: style.border,
        borderRadius: 16,
        background: style.background,
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          flexShrink: 0,
          padding: "4px 14px",
          borderRadius: 999,
          background: style.badgeBackground,
          color: style.badgeColor,
          fontSize: 12,
          fontWeight: 700,
          lineHeight: "20px",
        }}
      >
        数据来源
      </span>
      <div style={{ display: "grid", gap: 4 }}>
        <p style={{ color: style.titleColor, fontSize: 14, fontWeight: 700, lineHeight: "22px", margin: 0 }}>
          {banner.title}
        </p>
        <p style={{ color: style.bodyColor, fontSize: 13, lineHeight: "20px", margin: 0 }}>
          {banner.summary}
        </p>
      </div>
    </section>
  );
}
