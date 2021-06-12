
var chartData = JSON.parse(document.getElementById("chartData").textContent);

var spec = {
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "A simple bar chart with embedded data.",
  "data": {
    "values": chartData
  },
  "mark": "bar",
  "encoding": {
    "color": {
            "field": "a",
            "type": "nominal",
            "legend": null,
            "scale": {"scheme": {"name": "viridis", "extent": [1, 0]}}
        },
        "tooltip": [
            {"field": "a", "type": "nominal", "title": "Challenge"},
            {"field": "b", "type": "quantitative", "title": "Number of Participants", "format": ".0f"}
        ],
    "y": {"field": "a", "type": "nominal", "axis": {"labelAngle": 0}, "title": null},
    "x": {"field": "b", "type": "quantitative", "title": "Number of Participants"}
  }
}

// TODO Update this and the source data
vegaEmbed('#participantsGeoChart', spec, {"actions": false});
