/**
 * charts.js
 *
 * Real-time Charting Engine using Chart.js.
 * Renders Chamber Temperature vs Setpoint, Compressor Cooling Power, and Door Disturbances.
 */

class TelemetryChartManager {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.chart = null;
    this.initChart();
  }

  initChart() {
    if (!this.canvas || typeof Chart === 'undefined') {
      console.warn('Chart.js not loaded or canvas missing.');
      return;
    }

    this.chart = new Chart(this.ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Chamber Temp (°C)',
            data: [],
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            borderWidth: 2.5,
            fill: false,
            tension: 0.2,
            yAxisID: 'yTemp'
          },
          {
            label: 'Setpoint (°C)',
            data: [],
            borderColor: '#10b981',
            borderWidth: 2,
            borderDash: [6, 6],
            fill: false,
            pointRadius: 0,
            yAxisID: 'yTemp'
          },
          {
            label: 'Compressor Cooling (W)',
            data: [],
            borderColor: 'rgba(168, 85, 247, 0.75)',
            backgroundColor: 'rgba(168, 85, 247, 0.12)',
            borderWidth: 1.5,
            fill: true,
            tension: 0.1,
            yAxisID: 'yPower'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: { color: '#94a3b8', font: { family: 'Outfit', size: 12 } }
          },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.95)',
            titleColor: '#f8fafc',
            bodyColor: '#cbd5e1',
            borderColor: 'rgba(255, 255, 255, 0.15)',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Simulated Time (Minutes)', color: '#64748b' },
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#94a3b8',
              maxTicksLimit: 12,
              maxRotation: 0,
              minRotation: 0
            }
          },
          yTemp: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'Temperature (°C)', color: '#38bdf8' },
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8' }
          },
          yPower: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: 'Cooling Power (W)', color: '#a855f7' },
            grid: { drawOnChartArea: false },
            ticks: { color: '#94a3b8' }
          }
        }
      }
    });
  }

  updateData(history) {
    if (!this.chart || !history || !history.time_s) return;

    const timesMin = history.time_s.map(t => (t / 60.0).toFixed(1));
    this.chart.data.labels = timesMin;
    this.chart.data.datasets[0].data = history.temperature_degc;
    this.chart.data.datasets[1].data = history.setpoint_degc;
    this.chart.data.datasets[2].data = history.cooling_power_w;

    this.chart.update('none');
  }
}

window.TelemetryChartManager = TelemetryChartManager;
