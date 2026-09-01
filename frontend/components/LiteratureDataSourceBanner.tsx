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
    background: "var(--qiyan-status-success-bg)",
    border: "1px solid var(--qiyan-status-success-line)",
    badgeBackground: "rgba(13, 148, 136, 0.14)",
    badgeColor: "var(--qiyan-teal-dark)",
    titleColor: "var(--qiyan-teal-dark)",
    bodyColor: "#3d5a52",
  },
  live: {
    background: "#eef4fd",
    border: "1px solid #c3d9f6",
    badgeBackground: "rgba(37, 99, 235, 0.1)",
    badgeColor: "#1d4ed8",
    titleColor: "#1d4ed8",
    bodyColor: "#3b4f6e",
  },
  sample: {
    background: "var(--qiyan-status-warning-bg)",
    border: "1px solid var(--qiyan-status-warning-line)",
    badgeBackground: "rgba(180, 83, 9, 0.12)",
    badgeColor: "var(--qiyan-status-warning-text)",
    titleColor: "var(--qiyan-status-warning-text)",
    bodyColor: "#7c5a10",
  },
  upload: {
    background: "#f4f0fd",
    border: "1px solid #d8cdf5",
    badgeBackground: "rgba(109, 40, 217, 0.1)",
    badgeColor: "#6d28d9",
    titleColor: "#6d28d9",
    bodyColor: "#54457a",
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
        borderRadius: 14,
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
