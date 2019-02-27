"use strict";

$(document).ready(function () {
    google.charts.load('current', {'packages': ['geochart']});
    google.charts.setOnLoadCallback(drawGeoCharts);

    function drawGeoCharts() {
        google.visualization.mapsApiKey = '{{ geochart_api_key }}';
        var charts = document.querySelectorAll('[data-geochart]');

        for (var i = 0; i < charts.length; i++) {
            try {
                drawGeoChart(charts[i]);
            } catch (err) {
                console.log(err);
            }
        }
    }

    function drawGeoChart(element) {
        var array = JSON.parse(element.dataset['geochart']);
        var data = google.visualization.arrayToDataTable(array);
        var options = {
            colorAxis: {
                colors: [
                    '#440154',
                    '#32658e',
                    '#20a486',
                    '#63cb5f',
                    '#a8db34',
                    '#d0e11c',
                    '#e7e419',
                    '#f1e51d',
                    '#f8e621',
                    '#fbe723',
                    '#fbe723',
                    '#fde725',
                    '#fde725',
                    '#fde725',
                    '#fde725',
                    '#fde725'
                ]
            },
            backgroundColor: '#c9eeff'
        };
        var chart = new google.visualization.GeoChart(element);
        chart.draw(data, options);
    }
});
