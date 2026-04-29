"use client";

import { ArcElement, Chart as ChartJS, Legend, LineElement, LinearScale, PointElement, CategoryScale, Tooltip } from "chart.js";
import { Doughnut, Line } from "react-chartjs-2";

ChartJS.register(ArcElement, CategoryScale, LinearScale, PointElement, LineElement, Legend, Tooltip);

export function ProbabilityChart({ values }: { values: [number, number, number] }) {
  return (
    <Doughnut
      data={{
        labels: ["Normal", "High-Stress", "High-Risk"],
        datasets: [
          {
            data: values.map((value) => Math.round(value * 100)),
            backgroundColor: ["#0f766e", "#d89b1d", "#d95d39"],
            borderWidth: 0
          }
        ]
      }}
      options={{
        responsive: true,
        plugins: {
          legend: { position: "bottom" }
        },
        cutout: "64%"
      }}
    />
  );
}

export function RiskTrendChart({ points }: { points: Array<{ date: string; value: number }> }) {
  return (
    <Line
      data={{
        labels: points.map((point) => point.date),
        datasets: [
          {
            label: "Risk class",
            data: points.map((point) => point.value),
            borderColor: "#2b6cb0",
            backgroundColor: "#2b6cb0",
            tension: 0.25
          }
        ]
      }}
      options={{
        responsive: true,
        scales: {
          y: { min: 0, max: 2, ticks: { stepSize: 1 } }
        },
        plugins: {
          legend: { display: false }
        }
      }}
    />
  );
}
