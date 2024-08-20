$(document).ready(function () {
    $(".table").each(function () {
        $(this).DataTable({
            pageLength: 100,
            order: [[1, "asc"]],
        });
    });
});

$(window).resize(function () {
    $(".table").each(function () {
        $(this).DataTable().columns.adjust();
    });
});
