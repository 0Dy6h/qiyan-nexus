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
    background: "#f0fdfa",
    border: "1px solid #99f6e4",
    badgeBackground: "#ccfbf1",
    badgeColor: "#115e59",
    titleColor: "#115e59",
    bodyColor: "#0f766e",
  },
  live: {
    background: "#eff6ff",
    border: "1px solid #bfdbfe",
    badgeBackground: "#dbeafe",
    badgeColor: "#1d4ed8",
    titleColor: "#1e3a8a",
    bodyColor: "#1d4ed8",
  },
  sample: {
    background: "#fff7ed",
    border: "1px solid #fdba74",
    badgeBackground: "#fed7aa",
    badgeColor: "#9a3412",
    titleColor: "#9a3412",
    bodyColor: "#c2410c",
  },
  upload: {
    background: "#faf5ff",
    border: "1px solid #d8b4fe",
    badgeBackground: "#ede9fe",
    badgeColor: "#6d28d9",
    titleColor: "#5b21b6",
    bodyColor: "#6d28d9",
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
        borderRadius: 12,
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
