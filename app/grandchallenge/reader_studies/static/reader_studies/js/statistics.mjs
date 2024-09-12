$(document).ready(() => {
    $(".table").each(function () {
        $(this).DataTable({
            pageLength: 100,
            order: [[1, "asc"]],
        });
    });
});

$(window).resize(() => {
    $(".table").each(function () {
        $(this).DataTable().columns.adjust();
    });
});
