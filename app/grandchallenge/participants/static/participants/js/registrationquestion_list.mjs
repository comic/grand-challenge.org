$(document).ready(() => {
    $("#registrationQuestionsTable").DataTable({
        order: [[0, "asc"]],
        pageLength: 10,
        columnDefs: [
            {
                targets: [3, 4],
                searchable: false,
                orderable: false,
            },
        ],
    });
});
