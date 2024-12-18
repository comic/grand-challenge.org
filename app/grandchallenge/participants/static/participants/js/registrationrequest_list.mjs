$(document).ready(() => {
    $("#participantsTable").DataTable({
        order: [[0, "desc"]],
        pageLength: 10,
    });
});
