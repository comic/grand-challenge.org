import { renderVegaChartsObserver } from "../../js/charts/render_charts.mjs";
import { getCookie } from "../../js/get_cookie.mjs";

const defaultSortColumn = JSON.parse(
    document.getElementById("defaultSortColumn").textContent,
);
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
        ajax: {
            url: ".",
            type: "POST",
            headers: {
                "X-CSRFToken": getCookie("_csrftoken"),
            },
        },
        ordering: true,
        drawCallback: settings => {
            // trigger htmx process after the page has been updated.
            htmx.process("#ajaxDataTable");
        },
    });
});
