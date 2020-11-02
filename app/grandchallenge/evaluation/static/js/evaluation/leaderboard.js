const SELECT_TEXT = "Select results for comparison"
const MAX_NUM_RESULTS_WARNING = 6

const observableURL = JSON.parse(document.getElementById("observableURL").textContent)
const observableIframeURL = JSON.parse(document.getElementById("observableIframeURL").textContent)
const extraResultsColumns = JSON.parse(document.getElementById("extraResultsColumns").textContent)
const scoringMethodChoice = JSON.parse(document.getElementById("scoringMethodChoice").textContent)
const absoluteScore = JSON.parse(document.getElementById("absoluteScore").textContent)

let resultsTable = $('#resultsTable')


$(document).ready(function () {
    // Clean results on init
    localStorage.removeItem('compareResults')

    let table = resultsTable.DataTable({
        // The column index of the default sort, must match the table set up.
        order: [[observableURL !== "" ? 1 : 0, "asc"]],
        lengthChange: false,
        pageLength: 50,
        serverSide: true,
        ajax: {
            url: "",
        },
        columnDefs: [
            {
                targets: 'nonSortable',
                searchable: false,
                orderable: false,
                visible: true
            },
            {
                targets: 'toggleable',
                visible: false,
            }
        ],
        ordering: true,
        autoWidth: false,
        dom: getDOMTemplate(),
        buttons: getDataTablesButtons(),
        scrollX: true
    });

    let button = `<button type="button" id="compare-results-button" class="btn btn-link"
                    onclick="updateCompareIframe()" data-toggle="modal" data-target="#compareModal"
                    disabled>
                ${SELECT_TEXT}
                </button>`

    let checkbox = `<span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="Deselect all results">
                        <input type="checkbox" id="generalCheckbox"/>
                    </span>`

    $('table thead th.sorting_disabled').html(checkbox)
    let generalCheckbox = $('#generalCheckbox')
    generalCheckbox.prop('indeterminate', true).hide()

    if (observableURL !== "") {
        $('#compare-buttons-group').html(button)
    }

    let compareResultsButton = $('#compare-results-button')

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

    // On click on General checkbox
    generalCheckbox.on('click', function () {
        generalCheckbox.hide()
        // Clean up all the checkboxes
        localStorage.removeItem('compareResults')
        $(`.checkboxResult`).prop('checked', false)
        compareResultsButton.prop('disabled', true).text(SELECT_TEXT).removeClass('btn-primary').addClass('btn-link')
        $('#compare-warning-alert').slideUp();
    })

    // On click on the table checkboxes
    resultsTable.on('click', function (e) {
        if ($(e.target).is(':checkbox')) {

            // Get the existing data from localstorage or create {}
            let existing = JSON.parse(localStorage.getItem('compareResults')) || {};
            let resultId = $(e.target).val()

            // Add or remove data to the object
            if ($(e.target).is(':checked')) {
                existing[resultId] = true
                generalCheckbox.prop('indeterminate', true).show()
            } else {
                delete existing[resultId];
            }

            // Modify compare results button
            if (Object.entries(existing).length === 1) {
                compareResultsButton.prop('disabled', false)
                    .text(`Visualise result`)
                    .removeClass('btn-link').addClass('btn-primary')
            } else if (Object.entries(existing).length > 1) {
                compareResultsButton.prop('disabled', false)
                    .text(`Compare ${Object.entries(existing).length} results`)
                    .removeClass('btn-link').addClass('btn-primary')
            } else {
                compareResultsButton.text(SELECT_TEXT).prop('disabled', true)
                    .removeClass('btn-primary').addClass('btn-link')
            }

            // Toggle alert too many results
            let entriesAlert = $('#compare-warning-alert')
            Object.entries(existing).length >= MAX_NUM_RESULTS_WARNING
                ? entriesAlert.removeClass("d-none")
                : entriesAlert.addClass("d-none")

            // Remove General Checkbox
            if (Object.entries(existing).length === 0) {
                generalCheckbox.hide()
                compareResultsButton.text(SELECT_TEXT).prop('disabled', true)
                    .removeClass('btn-primary').addClass('btn-link')
            }

            // Save current state to localStorage
            localStorage.setItem('compareResults', JSON.stringify(existing));
        }
    })
});

$(window).resize(function () {
    resultsTable.DataTable().columns.adjust()
});

function updateCompareIframe() {
    let search = new URLSearchParams(Object.keys(JSON.parse(localStorage.getItem('compareResults'))).map(pk => ["pk", pk]))
    let notebook = document.getElementById('observableNotebook')

    notebook.src = ""
    notebook.src = `${observableIframeURL}?${search.toString()}`;
}

function getDOMTemplate() {
    let DOM = "<'row'<'col-12'f>>"

    if (extraResultsColumns.length > 0 || scoringMethodChoice !== absoluteScore || observableURL !== "") {
        DOM += "<'row'<'#compare-buttons-group.col-md-6'><'col px-0 text-right'B>>"
    }

    DOM += "<'row'<'col-12'tr>><'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>"
    return DOM
}

function getDataTablesButtons() {
    if (extraResultsColumns.length > 0 || scoringMethodChoice !== absoluteScore) {
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