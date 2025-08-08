from django.templatetags.static import static


def bar(*, values, lookup, title):
    chart = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "padding": 0,
        "title": title,
        "data": {"values": values},
        "mark": "bar",
        "encoding": {
            "x": {
                "field": "Month",
                "type": "temporal",
                "timeUnit": "yearmonth",
            },
            "y": {
                "field": lookup,
                "type": "quantitative",
            },
            "tooltip": [
                {
                    "field": "Month",
                    "type": "temporal",
                    "timeUnit": "yearmonth",
                },
                {"field": lookup, "type": "quantitative"},
            ],
        },
    }

    totals = sum(datum[lookup] for datum in values)

    return {"chart": chart, "totals": totals}


def stacked_bar(*, values, lookup, title, facet, domain):
    domain = dict(domain)

    totals = {str(d): 0 for d in domain.values()}
    for datum in values:
        datum[facet] = domain[datum[facet]]
        totals[str(datum[facet])] += datum[lookup]

    chart = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "padding": 0,
        "title": title,
        "data": {"values": values},
        "mark": "bar",
        "encoding": {
            "x": {
                "field": "Month",
                "type": "temporal",
                "timeUnit": "yearmonth",
            },
            "y": {
                "field": lookup,
                "type": "quantitative",
                "stack": True,
            },
            "tooltip": [
                {
                    "field": "Month",
                    "type": "temporal",
                    "timeUnit": "yearmonth",
                },
                {"field": facet, "type": "nominal"},
                {"field": lookup, "type": "quantitative"},
            ],
            "color": {
                "field": facet,
                "scale": {
                    "domain": list(domain.values()),
                },
                "type": "nominal",
            },
        },
    }

    return {"chart": chart, "totals": totals}


def horizontal_bar(*, values, lookup, title):
    url_lookup = "absolute_url"
    challenge_name_lookup = "short_name"
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "padding": 0,
        "data": {"values": values},
        "mark": "bar",
        "encoding": {
            "color": {
                "field": lookup,
                "type": "nominal",
                "legend": None,
                "scale": {"scheme": {"name": "viridis", "extent": [0, 1]}},
            },
            "tooltip": [
                {
                    "field": challenge_name_lookup,
                    "type": "nominal",
                    "title": "Challenge",
                },
                {
                    "field": lookup,
                    "type": "quantitative",
                    "title": title,
                    "format": ".0f",
                },
            ],
            "y": {
                "field": challenge_name_lookup,
                "type": "nominal",
                "axis": {"labelAngle": 0},
                "title": None,
                "sort": "-x",
            },
            "x": {
                "field": lookup,
                "type": "quantitative",
                "title": title,
                "axis": {"tickMinStep": "1", "format": ".0f"},
            },
            "href": {"field": url_lookup, "type": "nominal"},
        },
    }


def world_map(*, values):
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "height": "container",
        "padding": 0,
        "view": {"stroke": "transparent", "fill": "#c9eeff"},
        "data": {
            "url": static("js/world-atlas/countries-110m.json"),
            "format": {"type": "topojson", "feature": "countries"},
        },
        "transform": [
            {
                "lookup": "id",
                "from": {
                    "data": {"values": values},
                    "key": "id",
                    "fields": ["participants"],
                },
                "default": 0.01,
            }
        ],
        "projection": {"type": "equalEarth"},
        "mark": {
            "type": "geoshape",
            "stroke": "#757575",
            "strokeWidth": 0.5,
        },
        "encoding": {
            "color": {
                "field": "participants",
                "type": "quantitative",
                "scale": {
                    "scheme": "viridis",
                    "domainMin": 1,
                    "type": "log",
                },
                "legend": None,
                "condition": {
                    "test": "datum['participants'] === 0.01",
                    "value": "#eee",
                },
            },
            "tooltip": [
                {
                    "field": "properties.name",
                    "type": "nominal",
                    "title": "Location",
                },
                {
                    "field": "participants",
                    "type": "quantitative",
                    "title": "Participants",
                    "format": ".0f",
                },
            ],
        },
    }


def components_line(*, values, title, single_thread_limit, tooltip):
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "padding": 0,
        "title": title,
        "data": {"values": values},
        "layer": [
            {
                "transform": [
                    {"calculate": "100*datum.Percent", "as": "Percent100"},
                ],
                "encoding": {
                    "x": {
                        "timeUnit": "yearmonthdatehoursminutesseconds",
                        "field": "Timestamp",
                        "title": "Local Time",
                    },
                    "y": {
                        "field": "Percent100",
                        "type": "quantitative",
                        "title": "Utilization / %",
                        "scale": {"domain": [0, 100]},
                    },
                    "color": {"field": "Metric", "type": "nominal"},
                },
                "layer": [
                    {"mark": "line"},
                    {
                        "transform": [
                            {"filter": {"param": "hover", "empty": False}}
                        ],
                        "mark": "point",
                    },
                ],
            },
            {
                "transform": [
                    {
                        "pivot": "Metric",
                        "value": "Percent",
                        "groupby": ["Timestamp"],
                    }
                ],
                "mark": "rule",
                "encoding": {
                    "opacity": {
                        "condition": {
                            "value": 0.3,
                            "param": "hover",
                            "empty": False,
                        },
                        "value": 0,
                    },
                    "tooltip": tooltip,
                    "x": {
                        "timeUnit": "yearmonthdatehoursminutesseconds",
                        "field": "Timestamp",
                        "title": "Local Time",
                    },
                },
                "params": [
                    {
                        "name": "hover",
                        "select": {
                            "type": "point",
                            "fields": ["Timestamp"],
                            "nearest": True,
                            "on": "mouseover",
                            "clear": "mouseout",
                        },
                    }
                ],
            },
            {
                "data": {"values": [{}]},
                "mark": {"type": "rule", "strokeDash": [8, 8]},
                "encoding": {"y": {"datum": single_thread_limit}},
            },
            {
                "data": {"values": [{}]},
                "mark": {"type": "text", "baseline": "line-bottom"},
                "encoding": {
                    "text": {"datum": "Single CPU Thread"},
                    "y": {"datum": single_thread_limit},
                },
            },
        ],
    }
