document.addEventListener("DOMContentLoaded", event => {
    $("#challengeCostsOverviewTable").DataTable({
        order: [[2, "desc"]],
        lengthChange: false,
        pageLength: 100,
    });
});
