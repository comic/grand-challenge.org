const runtimeMetricsData = JSON.parse(document.getElementById("runtimeMetricsData").textContent);

function display_chart() {
    vegaEmbed("#runtimeMetricsChart", runtimeMetricsData, {"actions": false});
}

display_chart();

$('#v-pills-logs-tab').on('shown.bs.tab', function () {
    display_chart();
})
