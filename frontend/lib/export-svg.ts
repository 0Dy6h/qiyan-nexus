/**
 * Export SVG element to PNG using canvas
 */
export async function exportSvgToPng(
  svgElement: SVGSVGElement,
  filename: string = "network-graph.png"
): Promise<void> {
  const svgString = new XMLSerializer().serializeToString(svgElement);
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");

  if (!ctx) {
    throw new Error("Failed to get canvas 2D context");
  }

  const viewBox = svgElement.viewBox.baseVal;
  const width = viewBox.width || svgElement.clientWidth || 1000;
  const height = viewBox.height || svgElement.clientHeight || 600;

  // Use 2x scale for better quality
  const scale = 2;
  canvas.width = width * scale;
  canvas.height = height * scale;
  ctx.scale(scale, scale);

  // Fill white background
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  const img = new Image();
  const svgBlob = new Blob([svgString], {
    type: "image/svg+xml;charset=utf-8",
  });
  const url = URL.createObjectURL(svgBlob);

  return new Promise((resolve, reject) => {
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);

      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error("Failed to create PNG blob"));
          return;
        }

        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(downloadUrl);
        resolve();
      }, "image/png");
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Failed to load SVG image"));
    };

    img.src = url;
  });
}

/**
 * Export SVG element as SVG file
 */
export function exportSvgToSvg(
  svgElement: SVGSVGElement,
  filename: string = "network-graph.svg"
): void {
  const svgString = new XMLSerializer().serializeToString(svgElement);
  const blob = new Blob([svgString], {
    type: "image/svg+xml;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
