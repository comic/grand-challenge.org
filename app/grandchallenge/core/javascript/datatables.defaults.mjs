import $ from "jquery";

import DataTable from "datatables.net-bs4";
import "datatables.net-buttons-bs4";

Object.assign(DataTable.defaults, {
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
 * Other attributes prefixed with `data-dt-` can be used to configure DataTable
 * Example:
 * ```html
 * <table data-data-table data-dt-page-length="50" data-dt-order='[[0, "asc"]]'>
 * ```
 */
const DT_ATTRIBUTE_PREFIX = "data-dt-";
const DT_INITIALIZED_ATTRIBUTE = "data-dt-initialized";
document.addEventListener("DOMContentLoaded", () => {
    for (const table of document.querySelectorAll("table[data-data-table]")) {
        table.removeAttribute("data-data-table");
        if (table.hasAttribute(DT_INITIALIZED_ATTRIBUTE)) {
            continue; // Skip if already initialized
        }
        const options = {};
        for (const attr of table.attributes) {
            if (attr.name.startsWith(DT_ATTRIBUTE_PREFIX)) {
                // Convert data-dt-foo-bar to fooBar
                const camelKey = attr.name
                    .slice(DT_ATTRIBUTE_PREFIX.length)
                    .replace(/-([a-z])/g, (_, c) => c.toUpperCase());
                let value = attr.value;
                try {
                    value = JSON.parse(value);
                } catch {}
                options[camelKey] = value;
            }
        }
        // Prefer DataTable global, fallback to jQuery if available
        if (typeof window.DataTable !== "undefined") {
            new window.DataTable(table, options);
        } else if (
            typeof window.jQuery !== "undefined" &&
            window.jQuery.fn.dataTable
        ) {
            window.jQuery(table).DataTable(options);
        } else {
            console.warn("DataTables is not available for", table);
        }
        table.setAttribute(DT_INITIALIZED_ATTRIBUTE, "true");
    }
});
