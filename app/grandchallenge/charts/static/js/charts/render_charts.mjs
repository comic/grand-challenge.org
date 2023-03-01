function renderVegaLiteChart(element) {
    const spec = JSON.parse(element.children[0].textContent);
    vegaEmbed(element, spec, {"actions": false});
}

document.addEventListener("DOMContentLoaded", function(event) {
    for (const element of document.getElementsByClassName("vega-lite-chart")) {
        renderVegaLiteChart(element);
    }
});
