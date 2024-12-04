document.addEventListener("DOMContentLoaded", () => {
    $("#evaluationsTable").DataTable({
        order: [[2, "desc"]],
    });
});
