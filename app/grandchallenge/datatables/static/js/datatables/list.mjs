import { renderVegaChartsObserver } from "../../js/charts/render_charts.mjs";

const defaultSortColumn = JSON.parse(
    document.getElementById("defaultSortColumn").textContent,
);
const textAlign = JSON.parse(document.getElementById("textAlign").textContent);
const defaultSortOrder = JSON.parse(
    document.getElementById("defaultSortOrder").textContent,
);
const ajaxURL = JSON.parse(document.getElementById("ajaxURL").textContent);

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadDataTable);
} else {
    loadDataTable();
}

function loadDataTable() {
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
            url: ajaxURL,
        },
        ordering: true,
        drawCallback: settings => {
            // trigger htmx process after the page has been updated.
            htmx.process("#ajaxDataTable");
        },
    });
}
