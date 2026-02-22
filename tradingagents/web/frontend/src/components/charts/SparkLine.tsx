import { useEffect, useRef } from "react";
import { createChart, type Time } from "lightweight-charts";

interface SparkLineProps {
  data: { time: string; value: number }[];
  color?: string;
  width?: number;
  height?: number;
}

export default function SparkLine({
  data,
  color = "#3b82f6",
  width = 120,
  height = 40,
}: SparkLineProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || data.length < 2) return;

    const chart = createChart(containerRef.current, {
      width,
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "transparent",
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      crosshair: {
        vertLine: { visible: false },
        horzLine: { visible: false },
      },
      handleScale: false,
      handleScroll: false,
    });

    const series = chart.addAreaSeries({
      lineColor: color,
      topColor: `${color}33`,
      bottomColor: `${color}05`,
      lineWidth: 2,
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    series.setData(
      data.map((d) => ({ time: d.time as Time, value: d.value }))
    );

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [data, color, width, height]);

  if (data.length < 2) return null;

  return <div ref={containerRef} style={{ width, height }} />;
}
