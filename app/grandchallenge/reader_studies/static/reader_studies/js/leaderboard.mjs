$(document).ready(() => {
    $(".table").each(function () {
        $(this).DataTable({
            pageLength: 100,
        });
    });
});

$(window).resize(() => {
    $(".table").each(function () {
        $(this).DataTable().columns.adjust();
    });
});
