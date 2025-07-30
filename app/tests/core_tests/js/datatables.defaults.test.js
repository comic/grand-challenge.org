require("datatables.net")(window, $);
require("datatables.net-bs4")(window, $);
require("floating-scroll");
require("../../../grandchallenge/core/javascript/datatables.defaults.mjs");

describe("datatables.defaults.mjs", () => {
    beforeEach(() => {
        // Reset the DOM
        document.body.innerHTML = `
<table id="test-table" data-data-table data-dt-page-length="50" data-dt-order='[[0, "asc"]]'>
    <thead>
        <tr>
            <th>Column 1</th>
            <th class="nonSortable">Column 2</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Row 1, Column 1</td>
            <td>Row 1, Column 2</td>
        </tr>
        <tr>
            <td>Row 2, Column 1</td>
            <td>Row 2, Column 2</td>
        </tr>
    </tbody>
</table>
        `;
    });

    test("DataTable is initialized from data attributes", () => {
        document.dispatchEvent(new Event("DOMContentLoaded"));

        const table = $("#test-table").DataTable();

        expect(table.page.len()).toBe(50);
        expect(table.order().length).toBe(1);
        expect(table.order()[0].length).toBe(2);
        expect(table.order()[0][0]).toBe(0);
        expect(table.order()[0][1]).toBe("asc");
    });

    test("Floating scroll is attached to the correct element", () => {
        document.dispatchEvent(new Event("DOMContentLoaded"));

        const element = $(".dt-scroll-body");
        expect(element.length).toBe(1);
        const flScrolls = element.children("div.fl-scrolls");
        expect(flScrolls.length).toBe(1);
    });

    test("Non-sortable columns are correctly configured", () => {
        document.dispatchEvent(new Event("DOMContentLoaded"));

        const table = $("#test-table").DataTable();
        expect(table.column(0).orderable()).toBe(true);
        expect(table.column(1).orderable()).toBe(false);
    });

    test("Column headers have title attributes", () => {
        document.dispatchEvent(new Event("DOMContentLoaded"));

        const table = $("#test-table").DataTable();

        const header = $(table.column(0).header());
        expect(header.attr("title")).toBe(
            "Activate to sort. Hold Shift to sort by multiple columns.",
        );
    });
});
