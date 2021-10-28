const allCharts = JSON.parse(document.getElementById("allCharts").textContent);
const vega_lite_defaults = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "width": "container",
    "padding": 0,
}

for (let i = 0; i < allCharts.length; i++) {
  const displayID = "#resultsChart_"+i;
  const chartData = allCharts[i];
  createResultsChart(chartData, displayID);
}

function createResultsChart(chartData, displayID) {
    const spec = {...vega_lite_defaults, ...chartData.valueOf()};
    vegaEmbed(displayID, spec, {"actions": false});
}
