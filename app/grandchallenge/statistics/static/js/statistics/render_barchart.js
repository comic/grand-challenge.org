const challengeRegistrations = JSON.parse(document.getElementById("challengeRegistrations").textContent);
const challengeSubmissions = JSON.parse(document.getElementById("challengeSubmissions").textContent);
const days = JSON.parse(document.getElementById("days").textContent);

createStackedBarChart(challengeRegistrations, "num_registrations_period", `Number of registrations last ${days} days`, "#registrationsChart");
createStackedBarChart(challengeSubmissions, "num_submissions_period", `Number of submissions last ${days} days`, "#submissionsChart");

function createStackedBarChart(chartData, statisticLookup, statisticTitle, displayID) {
    const challengeNameLookup = "short_name";
    const urlLookup = "absolute_url";
    const spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "padding": 0,
        "data": {
            "values": chartData
        },
        "mark": "bar",
        "encoding": {
            "color": {
                "field": statisticLookup,
                "type": "nominal",
                "legend": null,
                "scale": {"scheme": {"name": "viridis", "extent": [0, 1]}}
            },
            "tooltip": [
                {"field": challengeNameLookup, "type": "nominal", "title": "Challenge"},
                {"field": statisticLookup, "type": "quantitative", "title": statisticTitle, "format": ".0f"}
            ],
            "y": {
                "field": challengeNameLookup,
                "type": "nominal",
                "axis": {"labelAngle": 0},
                "title": null,
                "sort": "-x"
            },
            "x": {
                "field": statisticLookup,
                "type": "quantitative",
                "title": statisticTitle,
                "axis": {"tickMinStep": "1", "format": ".0f"}
            },
            "href": {"field": urlLookup, "type": "nominal"}
        }
    }

    vegaEmbed(displayID, spec, {"actions": false});
}
