import { renderVegaChartsObserver } from "../../js/charts/render_charts.mjs";

const defaultSortColumn = JSON.parse(
    document.getElementById("defaultSortColumn").textContent,
);
const textAlign = JSON.parse(document.getElementById("textAlign").textContent);
const defaultSortOrder = JSON.parse(
    document.getElementById("defaultSortOrder").textContent,
);

document.addEventListener("DOMContentLoaded", () => {
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
            ...$.fn.dataTable.defaults.columnDefs,
            {
                className: `align-middle text-${textAlign}`,
                targets: "_all",
            },
        ],
        ajax: {
            url: ".",
        },
        ordering: true,
        drawCallback: settings => {
            // trigger htmx process after the page has been updated.
            htmx.process("#ajaxDataTable");
        },
    });
});
