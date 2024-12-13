$.extend($.fn.dataTable.defaults, {
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
    const element = $(".dt-scroll-body");

    if (element.length === 0) {
        console.warn(
            "Warning: Element for floating-scroll attachment could not be located",
        );
    }

    element.floatingScroll();
});
