$.extend(true, DataTable.defaults, {
    scrollX: true,
    language: {
        paginate: {
            next: "Next",
            previous: "Previous",
        },
    },
    pagingType: "simple_numbers",
});

$(document).on("init.dt", () => {
    // Set up floating scroll, note that the target class only shows up when scrollX is set to true
    $(".dataTables_scrollBody").floatingScroll();
});
