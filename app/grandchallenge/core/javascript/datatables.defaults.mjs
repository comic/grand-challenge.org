async function initDataTables() {
    const { default: DataTable } = await import("datatables.net-bs4");
    const { default: $ } = await import("jquery");
    await import("datatables.net-buttons");
    await import("datatables.net-buttons-bs4");
    await import("datatables.net-bs4/css/dataTables.bootstrap4.css");
    await import("datatables.net-buttons-bs4/css/buttons.bootstrap4.css");
    await import("floating-scroll");
    await import("floating-scroll/dist/jquery.floatingscroll.css");
    const { renderVegaChartsObserver } = await import(
        "../../charts/javascript/render_charts.mjs"
    );

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
    for (const table of document.querySelectorAll("table[data-data-table]")) {
        table.removeAttribute("data-data-table");
        if (table.hasAttribute(DT_INITIALIZED_ATTRIBUTE)) {
            continue; // Skip if already initialized
        }
        let options = {};
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

        if (table.id === "ajaxDataTable") {
            const defaultSortColumn = JSON.parse(
                document.getElementById("defaultSortColumn").textContent,
            );
            const textAlign = JSON.parse(
                document.getElementById("textAlign").textContent,
            );
            const defaultSortOrder = JSON.parse(
                document.getElementById("defaultSortOrder").textContent,
            );
            renderVegaChartsObserver.observe(
                document.getElementById("ajaxDataTable"),
                {
                    childList: true,
                    subtree: true,
                },
            );
            const ajaxTableOptions = {
                order: [[defaultSortColumn, defaultSortOrder]],
                lengthChange: false,
                pageLength: 25,
                serverSide: true,
                columnDefs: [
                    ...DataTable.defaults.columnDefs,
                    {
                        className: `align-middle text-${textAlign}`,
                        targets: "_all",
                    },
                ],
                ajax: {
                    url: ".",
                },
                ordering: true,
                drawCallback: settings => {
                    // trigger htmx process after the page has been updated.
                    htmx.process("#ajaxDataTable");
                },
            };
            options = {
                ...options,
                ...ajaxTableOptions,
            };
        }

        new DataTable(table, options);
        table.setAttribute(DT_INITIALIZED_ATTRIBUTE, "true");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector("table[data-data-table]")) {
        initDataTables();
    }
});
