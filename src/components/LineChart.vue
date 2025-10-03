<template>
  <Line :data="chartData" :options="chartOptions" />
</template>

<script>
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip
} from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip
)

export default {
  name: 'LineChart',
  components: { Line },
  props: {
    chartConfig: {
      type: Object,
      default: () => ({
        is_mine: true,
        symb: "",
        data: [{
          "date": "2024-12-01",
          "value": 0
        },
        {
          "date": "2025-02-01",
          "value": 0
        },
        {
          "date": "2025-05-01",
          "value": 0
        }]
      })
    }
  },
  computed: {
    optimalDecimalPlaces() {
      const values = this.chartConfig.data.map(el => el.value);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min;

      if (range === 0) return 3;

      // Визначаємо кількість знаків залежно від діапазону
      if (range < 0.001) return 6;
      if (range < 0.01) return 5;
      if (range < 0.1) return 4;
      if (range < 1) return 3;
      return 2;
    },
    chartData() {
      return {
        labels: this.chartConfig.data.map(el => el.date.split("-").reverse().slice(0, 2).join(".")),
        datasets: [{
          backgroundColor: this.chartConfig.is_mine ? '#31FF80' : '#31CFFF',
          borderColor: this.chartConfig.is_mine ? '#31FF80' : '#31CFFF',
          borderWidth: 2,
          data: this.chartConfig.data.map(el => el.value),
          pointRadius: (ctx) => {
            return ctx.dataIndex === ctx.dataset.data.length - 1 ? 5 : 0
          },
          pointHoverRadius: (ctx) => {
            return ctx.dataIndex === ctx.dataset.data.length - 1 ? 5 : 0
          },
          pointBackgroundColor: 'white',
          pointBorderColor: this.chartConfig.is_mine ? '#31FF80' : '#31CFFF',
          pointBorderWidth: 2,
          pointStyle: 'circle',
          tension: .2,
        }]
      }
    },
    chartOptions() {
      const symb = this.chartConfig.symb;
      const decimalPlaces = this.optimalDecimalPlaces;

      return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          tooltip: {
            enabled: false // Вимикаємо спливаючі підказки
          }
        },
        scales: {
          x: {
            display: true,
            grid: {
              display: false // Прибираємо сітку на осі X
            },
            ticks: {
              font: {
                size: 5,
                padding: 0 // Розмір шрифта для підписів осі X
              },
              color: '#fff',
              padding: 0,
              labelOffset: 0
            },
            border: {
              color: '#ffffff50'  // Колір самої осі X
            }
          },
          y: {
            display: true,
            grid: {
              display: false // Прибираємо сітку на осі Y
            },
            ticks: {
              maxTicksLimit: 6,
              font: {
                size: 6// Розмір шрифта для підписів осі X
              },
              padding: 0,
              color: '#fff',
              labelOffset: 0,
              callback: function (value) {
                return Number(value).toFixed(decimalPlaces) + symb;
              }
            },
            border: {
              color: '#ffffff50' // Колір самої осі X
            }
          }
        }
      }
    }
  },
  data() {
    return {

    }
  }
}
</script>