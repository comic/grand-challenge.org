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
            targets: "nonSortable",
            searchable: false,
            orderable: false,
        },
    ],
    drawCallback: function () {
        const api = this.api();
        api.columns().every(function () {
            if (this.orderable) {
                this.header().setAttribute(
                    "title",
                    "Activate to sort. Hold Shift to sort by multiple columns.",
                );
            }
        });
    },
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
