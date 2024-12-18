document.addEventListener("DOMContentLoaded", event => {
    $("#phaseCostsOverviewTable").DataTable({
        order: [[0, "asc"]],
        lengthChange: false,
        pageLength: 100,
    });
});
