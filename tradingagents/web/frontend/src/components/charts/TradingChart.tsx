import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type ISeriesApi, type SeriesMarker, type Time } from "lightweight-charts";

interface DataPoint {
  time: string;
  value: number;
}

interface Marker {
  time: string;
  position: "belowBar" | "aboveBar";
  color: string;
  shape: "arrowUp" | "arrowDown" | "circle";
  text: string;
}

interface TradingChartProps {
  equityCurve: DataPoint[];
  markers?: Marker[];
  mode?: "equity" | "line";
  height?: number;
}

export default function TradingChart({
  equityCurve,
  markers = [],
  mode = "equity",
  height = 300,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const isDark = document.documentElement.getAttribute("data-theme") !== "light";

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: "transparent" },
        textColor: isDark ? "#9ca3af" : "#4b5563",
        fontFamily: "'Inter', sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: isDark ? "rgba(55, 65, 81, 0.3)" : "rgba(229, 231, 235, 0.5)" },
        horzLines: { color: isDark ? "rgba(55, 65, 81, 0.3)" : "rgba(229, 231, 235, 0.5)" },
      },
      rightPriceScale: {
        borderColor: isDark ? "#1f2937" : "#e5e7eb",
      },
      timeScale: {
        borderColor: isDark ? "#1f2937" : "#e5e7eb",
        timeVisible: false,
      },
      crosshair: {
        vertLine: { color: isDark ? "#374151" : "#d1d5db", width: 1, style: 2 },
        horzLine: { color: isDark ? "#374151" : "#d1d5db", width: 1, style: 2 },
      },
      autoSize: true,
    });

    const lineColor = mode === "equity" ? "#3b82f6" : "#34d399";

    const series = chart.addAreaSeries({
      lineColor,
      topColor: `${lineColor}33`,
      bottomColor: `${lineColor}05`,
      lineWidth: 2,
    });

    const formattedData = equityCurve.map((d) => ({
      time: d.time as Time,
      value: d.value,
    }));

    series.setData(formattedData);

    if (markers.length > 0) {
      const sortedMarkers: SeriesMarker<Time>[] = markers
        .map((m) => ({
          time: m.time as Time,
          position: m.position,
          color: m.color,
          shape: m.shape,
          text: m.text,
        }))
        .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

      series.setMarkers(sortedMarkers);
    }

    chart.timeScale().fitContent();

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [equityCurve, markers, mode, height]);

  return (
    <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />
  );
}
