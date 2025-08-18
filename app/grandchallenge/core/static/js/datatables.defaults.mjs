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

/**
 * Enable DataTable by setting data attributes on the table element.
 * This allows for easy configuration without needing to write JavaScript.
 * `data-data-table` is required to enable DataTable on the table.
 * Other attributes can be used to configure DataTable
 * Example:
 * ```html
 * <table data-data-table data-page-length="50" data-order='[[0, "asc"]]'>
 * ```
 */
document.addEventListener("DOMContentLoaded", () => {
    for (const table of document.querySelectorAll("table[data-data-table]")) {
        // Prefer DataTable global, fallback to jQuery if available
        if (typeof window.DataTable !== "undefined") {
            new window.DataTable(table);
        } else if (
            typeof window.jQuery !== "undefined" &&
            window.jQuery.fn.dataTable
        ) {
            window.jQuery(table).DataTable();
        } else {
            console.warn("DataTables is not available for", table);
        }
    }
});
