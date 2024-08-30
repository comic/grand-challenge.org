import { renderVegaChartsObserver } from "/static/js/charts/render_charts.mjs";

const defaultSortColumn = JSON.parse(
    document.getElementById("defaultSortColumn").textContent,
);
const textAlign = JSON.parse(document.getElementById("textAlign").textContent);
const defaultSortOrder = JSON.parse(
    document.getElementById("defaultSortOrder").textContent,
);

$(document).ready(() => {
    renderVegaChartsObserver.observe(document.getElementById("ajaxDataTable"), {
        childList: true,
        subtree: true,
    });

    $("#ajaxDataTable").DataTable({
        order: [[defaultSortColumn, defaultSortOrder]],
        lengthChange: false,
        pageLength: 25,
        serverSide: true,
        columnDefs: [
            {
                targets: "nonSortable",
                searchable: false,
                orderable: false,
            },
            {
                className: `align-middle text-${textAlign}`,
                targets: "_all",
            },
        ],
        ajax: {
            url: "",
            dataSrc: json => {
                const table = $("#ajaxDataTable").DataTable();
                for (const [index, visible] of json.showColumns.entries()) {
                    table.column(index).visible(visible);
                }
                return json.data;
            },
        },
        ordering: true,
    });
});
