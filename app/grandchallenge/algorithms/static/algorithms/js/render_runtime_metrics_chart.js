const runtimeMetricsData = JSON.parse(document.getElementById("runtimeMetricsData").textContent);
vegaEmbed("#runtimeMetricsChart", runtimeMetricsData, {"actions": false});
