const countryParticipants = JSON.parse(document.getElementById("countryParticipants").textContent);
const spec = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "width": "container",
    "height": "container",
    "padding": 0,
    "view": {
        "stroke": "transparent",
        "fill": "#c9eeff"
    },
    "data": {
        "url": "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json",
        "format": {"type": "topojson", "feature": "countries"}
    },
    "transform": [
        {
            "lookup": "id",
            "from": {
                "data": {"values": countryParticipants},
                "key": "id",
                "fields": ["participants"]
            },
            "default": 0.01
        }
    ],
    "projection": {"type": "equalEarth"},
    "mark": {"type": "geoshape", "stroke": "#757575", "strokeWidth": 0.5},
    "encoding": {
        "color": {
            "field": "participants",
            "type": "quantitative",
            "scale": {"scheme": "viridis", "domainMin": 1, "type": "log"},
            "legend": null,
            "condition": {"test": "datum['participants'] === 0.01", "value": "#eee"}
        },
        "tooltip": [
            {"field": "properties.name", "type": "nominal", "title": "Country"},
            {"field": "participants", "type": "quantitative", "title": "Participants", "format": ".0f"}
        ]
    }
};

vegaEmbed('#participantsGeoChart', spec, {"actions": false});
