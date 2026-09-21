// Dynamic Chart.js visualizations for Personal Finance Advisor Bot

let expenseDonutChart = null;
let budgetBarChart = null;
let trendLineChart = null;
let incomeSourceChart = null;

// Modern vibrant color palette for categories
const CHART_COLORS = [
  "#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899",
  "#06b6d4", "#f97316", "#84cc16", "#6366f1", "#14b8a6"
];

async function loadDashboardCharts(month) {
  try {
    const res = await fetch(`/api/dashboard?month=${encodeURIComponent(month)}`);
    if (!res.ok) throw new Error("Network response was not ok");
    const data = await res.json();

    renderExpenseDonut(data.expense_by_category);
    renderBudgetPerformance(data.budget_performance);
    renderTrendLine(data.trend);
    renderIncomeSource(data.income_by_source);
  } catch (err) {
    console.error("Failed to load dashboard data:", err);
  }
}

function renderExpenseDonut(expenseData) {
  const ctx = document.getElementById("expenseDonutChart");
  if (!ctx) return;

  const labels = Object.keys(expenseData);
  const values = Object.values(expenseData);

  if (expenseDonutChart) expenseDonutChart.destroy();

  if (labels.length === 0) {
    // Show empty state placeholder in chart
    labels.push("No Expenses Yet");
    values.push(1);
  }

  expenseDonutChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: labels[0] === "No Expenses Yet" ? ["#334155"] : CHART_COLORS.slice(0, labels.length),
        borderWidth: 2,
        borderColor: "#0f172a"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#94a3b8", font: { family: "Inter", size: 12 } }
        }
      },
      cutout: "70%"
    }
  });
}

function renderBudgetPerformance(budgetData) {
  const ctx = document.getElementById("budgetBarChart");
  if (!ctx) return;

  if (budgetBarChart) budgetBarChart.destroy();

  if (!budgetData || !budgetData.has_budget || budgetData.labels.length === 0) {
    return;
  }

  budgetBarChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: budgetData.labels,
      datasets: [
        {
          label: "Actual Spent",
          data: budgetData.actuals,
          backgroundColor: budgetData.colors,
          borderRadius: 6
        },
        {
          label: "Budget Limit",
          data: budgetData.limits,
          backgroundColor: "rgba(255, 255, 255, 0.15)",
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#94a3b8", font: { family: "Inter" } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", font: { family: "Inter" } }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { family: "Inter" } }
        }
      }
    }
  });
}

function renderTrendLine(trendData) {
  const ctx = document.getElementById("trendLineChart");
  if (!ctx) return;

  if (trendLineChart) trendLineChart.destroy();

  trendLineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: trendData.labels,
      datasets: [
        {
          label: "Income",
          data: trendData.income,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          tension: 0.35,
          fill: true
        },
        {
          label: "Expenses",
          data: trendData.expenses,
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.05)",
          tension: 0.35,
          fill: true
        },
        {
          label: "Net Savings",
          data: trendData.savings,
          borderColor: "#38bdf8",
          borderDash: [5, 5],
          tension: 0.35
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", font: { family: "Inter" } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", font: { family: "Inter" } }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { family: "Inter" } }
        }
      }
    }
  });
}

function renderIncomeSource(sourceData) {
  const ctx = document.getElementById("incomeSourceChart");
  if (!ctx) return;

  const labels = Object.keys(sourceData);
  const values = Object.values(sourceData);

  if (incomeSourceChart) incomeSourceChart.destroy();

  if (labels.length === 0) {
    labels.push("No Income Logged");
    values.push(1);
  }

  incomeSourceChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: labels[0] === "No Income Logged" ? ["#334155"] : ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b"],
        borderWidth: 2,
        borderColor: "#0f172a"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#94a3b8", font: { family: "Inter", size: 11 } }
        }
      },
      cutout: "60%"
    }
  });
}
