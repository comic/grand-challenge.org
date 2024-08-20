$(document).ready(function () {
    $(".table").each(function () {
        $(this).DataTable({
            order: [[1, "desc"]],
            paging: false,
        });
    });
});
