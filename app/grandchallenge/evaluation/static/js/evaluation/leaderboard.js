const SELECT_TEXT = "Select results for comparison"
const MAX_NUM_RESULTS_WARNING = 6

const allowEvaluationComparison = JSON.parse(document.getElementById("allowEvaluationComparison").textContent)
const observableIframeURL = JSON.parse(document.getElementById("observableIframeURL").textContent)
const allowMetricsToggling = JSON.parse(document.getElementById("allowMetricsToggling").textContent)

let resultsTable = $('#resultsTable')
let selectedResults = {}


$(document).ready(function () {
    let table = resultsTable.DataTable({
        // The column index of the default sort, must match the table set up.
        order: [[allowEvaluationComparison === true ? 1 : 0, "asc"]],
        lengthChange: false,
        pageLength: 50,
        serverSide: true,
        ajax: {
            url: "",
            complete: updateCompareCheckBoxes,
        },
        columnDefs: [
            {
                targets: 'nonSortable',
                searchable: false,
                orderable: false,
            },
            {
                targets: 'toggleable',
                visible: false,
            }
        ],
        ordering: true,
        autoWidth: false,
        dom: getDataTablesDOMTemplate(),
        buttons: getDataTablesButtons(),
        scrollX: true
    });

    if (allowMetricsToggling === true) {
        resultsTable.on('column-visibility.dt', function () {
            let button = table.button(1).node();
            let visibility_columns = table.columns('.toggleable').visible();
            let not_all_visible = false;
            visibility_columns.each(function (value) {
                if (value === false) {
                    not_all_visible = true;
                    return false;
                }
            });
            if (!not_all_visible) {
                button.addClass('metrics-hidden');
                button.text('Hide additional metrics');
            } else {
                button.removeClass('metrics-hidden');
                button.text('Show all metrics');
            }
        });
    }

    if (allowEvaluationComparison === true) {
        $('#compare-buttons-group').html(
            `<button type="button" id="compare-results-button" class="btn btn-link" onclick="updateCompareIframe()" 
                     data-toggle="modal" data-target="#compareModal" disabled>
                ${SELECT_TEXT}
            </button>`
        )

        $('#compareEvaluationsHeader').html(
            `<span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="Deselect all results">
                <input type="checkbox" id="compareAllEvaluationsCheckbox"/>
            </span>`
        )

        let compareResultsButton = $('#compare-results-button')

        let compareAllEvaluationsCheckbox = $('#compareAllEvaluationsCheckbox')
        compareAllEvaluationsCheckbox.prop('indeterminate', true).hide()

        // On click on General checkbox
        compareAllEvaluationsCheckbox.on('click', function () {
            compareAllEvaluationsCheckbox.hide()
            selectedResults = {};
            $(`.compareEvaluationCheckbox`).prop('checked', false)
            compareResultsButton.prop('disabled', true).text(SELECT_TEXT).removeClass('btn-primary').addClass('btn-link')
            $('#compare-warning-alert').addClass("d-none");
        })

        // On click on the table checkboxes
        resultsTable.on('click', function (e) {
            if ($(e.target).is(':checkbox')) {
                const resultId = $(e.target).val()

                // Add or remove data to the object
                if ($(e.target).is(':checked')) {
                    selectedResults[resultId] = true
                    compareAllEvaluationsCheckbox.prop('indeterminate', true).show()
                } else {
                    delete selectedResults[resultId];
                }

                const numSelectedResults = Object.entries(selectedResults).length

                // Modify compare results button
                if (numSelectedResults === 1) {
                    compareResultsButton.prop('disabled', false)
                        .text(`Visualise result`)
                        .removeClass('btn-link').addClass('btn-primary')
                } else if (numSelectedResults > 1) {
                    compareResultsButton.prop('disabled', false)
                        .text(`Compare ${numSelectedResults} results`)
                        .removeClass('btn-link').addClass('btn-primary')
                } else {
                    compareResultsButton.prop('disabled', true)
                        .text(SELECT_TEXT)
                        .removeClass('btn-primary').addClass('btn-link')
                    compareAllEvaluationsCheckbox.hide()
                }

                // Toggle alert too many results
                let entriesAlert = $('#compare-warning-alert')
                numSelectedResults >= MAX_NUM_RESULTS_WARNING
                    ? entriesAlert.removeClass("d-none")
                    : entriesAlert.addClass("d-none")
            }
        })
    }
});

$(window).resize(function () {
    resultsTable.DataTable().columns.adjust()
});

function updateCompareIframe() {
    let search = new URLSearchParams(Object.keys(selectedResults).map(pk => ["pk", pk]))
    let notebook = document.getElementById('observableNotebook')

    notebook.src = `${observableIframeURL}?${search.toString()}`;
}

function getDataTablesDOMTemplate() {
    let DOM = "<'row'<'col-12'f>>"

    if (allowMetricsToggling === true || allowEvaluationComparison === true) {
        DOM += "<'row'<'#compare-buttons-group.col-md-6'><'col px-0 text-right'B>>"
    }

    DOM += "<'row'<'col-12'tr>><'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>"
    return DOM
}

function getDataTablesButtons() {
    if (allowMetricsToggling === true) {
        return [
            {
                extend: 'colvis',
                text: 'Additional metrics',
                columns: '.toggleable'
            },
            {
                text: 'Show all metrics',
                action: function (e, dt, node) {
                    if ($(node).hasClass('metrics-hidden')) {
                        dt.columns('.toggleable').visible(false);
                        $(node).removeClass('metrics-hidden');
                        $(node).text('Show all metrics');
                    } else {
                        dt.columns('.toggleable').visible(true);
                        $(node).addClass('metrics-hidden');
                        $(node).text('Hide additional metrics');
                    }
                }
            },
        ]
    } else {
        return []
    }
}

function updateCompareCheckBoxes() {
    $(".compareEvaluationCheckbox").filter(function () {
        return $(this).attr("value") in selectedResults
    }).prop('checked', true)
}
