$(document).ready(() => {
    $("table.sortable").dataTable({
        paginate: false,
        lengthChange: false,
        filter: false,
        info: false,
    });
});
