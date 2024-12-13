$.extend(true, DataTable.defaults, {
    scrollX: true,
    lengthChange: false,
    language: {
        paginate: {
            next: "Next",
            previous: "Previous",
        },
    },
    pagingType: "simple_numbers",
    columnDefs: [
        {
            // Prevents unexpected styling for dt-*-type datatypes
            // Only applies to client-side tables
            type: "string",
            targets: "_all",
        },
        {
            targets: "nonSortable",
            searchable: false,
            orderable: false,
        },
    ],
});

$(document).on("init.dt", () => {
    // Set up floating scroll, note that the target class only shows up when scrollX is set to true
    $(".dataTables_scrollBody").floatingScroll();
});
