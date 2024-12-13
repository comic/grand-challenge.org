$(document).ready(() => {
    $("#registrationQuestionsTable").DataTable({
        order: [[0, "asc"]],
        pageLength: 10,
    });
});
