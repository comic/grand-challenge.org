function renderVegaLiteChart(element) {
    const spec = JSON.parse(document.getElementById(element.dataset["vegaLiteChartKey"]).textContent);
    vegaEmbed(element, spec, {"actions": false});
}

document.addEventListener("DOMContentLoaded", function(event) {
    for (const element of document.getElementsByClassName("vega-lite-chart")) {
        renderVegaLiteChart(element);
    }
});
