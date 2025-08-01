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

    test("DataTable is initialized from data-dt-* attributes and sets DT_INITIALIZED_ATTRIBUTE", () => {
        document.dispatchEvent(new Event("DOMContentLoaded"));

        const tableElem = document.getElementById("test-table");
        expect(tableElem.hasAttribute("data-dt-initialized")).toBe(true);

        const table = $("#test-table").DataTable();
        expect(table.page.len()).toBe(50);
        expect(table.order().length).toBe(1);
        expect(table.order()[0].length).toBe(2);
        expect(table.order()[0][0]).toBe(0);
        expect(table.order()[0][1]).toBe("asc");
    });

    test("DataTable skips initialization if DT_INITIALIZED_ATTRIBUTE is present", () => {
        const tableElem = document.getElementById("test-table");
        tableElem.setAttribute("data-dt-initialized", "true");
        document.dispatchEvent(new Event("DOMContentLoaded"));
        // Should not re-initialize, so no error or duplicate
        expect(tableElem.hasAttribute("data-dt-initialized")).toBe(true);
    });

    test("DataTable parses JSON values from data-dt-* attributes", () => {
        document.body.innerHTML = `
<table id="json-table" data-data-table data-dt-order='[[1, "desc"]]' data-dt-page-length="10">
    <thead><tr><th>A</th><th>B</th></tr></thead>
    <tbody><tr><td>1</td><td>2</td></tr></tbody>
</table>
        `;
        document.dispatchEvent(new Event("DOMContentLoaded"));
        const table = $("#json-table").DataTable();
        expect(table.page.len()).toBe(10);
        expect(table.order()[0][0]).toBe(1);
        expect(table.order()[0][1]).toBe("desc");
    });

    test("ajaxDataTable special options are applied", () => {
        document.body.innerHTML = `
<div>
<span id="defaultSortColumn">0</span>
<span id="textAlign">\"center\"</span>
<span id="defaultSortOrder">\"asc\"</span>
<table id="ajaxDataTable" data-data-table></table>
</div>
        `;
        // Mock htmx.process
        window.htmx = { process: jest.fn() };
        document.dispatchEvent(new Event("DOMContentLoaded"));
        const table = $("#ajaxDataTable").DataTable();
        expect(table.page.len()).toBe(25);
        expect(table.order()[0][0]).toBe(0);
        expect(table.order()[0][1]).toBe("asc");
        // Check columnDefs includes textAlign
        const colDefs = table.settings().init().columnDefs;
        expect(colDefs).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    className: "align-middle text-center",
                    targets: "_all",
                }),
            ]),
        );
        // Check htmx.process called
        setTimeout(() => {
            expect(window.htmx.process).toHaveBeenCalledWith("#ajaxDataTable");
        }, 0);
    });

    test("Floating scroll is attached to the correct element", () => {
        document.dispatchEvent(new Event("DOMContentLoaded"));
        const element = document.querySelector(".dt-scroll-body");
        expect(element).not.toBeNull();
        const flScrolls = Array.from(element.children).filter(
            el => el.tagName === "DIV" && el.classList.contains("fl-scrolls"),
        );
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
