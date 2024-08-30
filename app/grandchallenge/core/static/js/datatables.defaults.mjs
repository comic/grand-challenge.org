$.extend(true, DataTable.defaults, {
    scrollX: true,
});

$(document).on("init.dt", event => {
    // This is a work-around to get the table to resize properly on extra-large Bootstrap viewport
    setTimeout($(event.target).DataTable().columns.adjust, 1000);

    // Set up floating scroll, note that the target class only shows up when scrollX is set to true
    handyScroll.mount(".dataTables_scrollBody");
});
