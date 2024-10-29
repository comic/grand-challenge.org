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
        responsive: {
            details: {
                renderer: (api, rowIdx, columns) => {
                    const data = $.map(columns, (col, i) =>
                        col.hidden
                            ? `<tr data-dt-row="${col.rowIndex}" data-dt-column="${col.columnIndex}"><td class="font-weight-bold">${col.title}:</td> <td>${col.data}</td></tr>`
                            : "",
                    ).join("");

                    return data ? $("<table/>").append(data) : false;
                },
            },
        },
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
        },
        ordering: true,
        initComplete: (settings, json) => {
            htmx.process("#ajaxDataTable");
        },
    });
});

$("#ajaxDataTable").on("init.dt", () => {
    // This is a work-around to get the table to resize properly on extra-large Bootstrap viewport
    setTimeout($("#ajaxDataTable").DataTable().columns.adjust, 1000);
});

$(window).resize(() => {
    $("#ajaxDataTable").DataTable().columns.adjust();
});
