const SELECT_TEXT = `Select 2 or more results for comparison`
const MAX_NUM_RESULTS_WARNING = 6

const allowEvaluationComparison = JSON.parse(document.getElementById("allowEvaluationComparison").textContent)
const observableComparisonURL = JSON.parse(document.getElementById("observableComparisonURL").textContent)
const allowEvaluationNavigation = JSON.parse(document.getElementById("allowEvaluationNavigation").textContent)
const observableDetailURL = JSON.parse(document.getElementById("observableDetailURL").textContent)
const allowMetricsToggling = JSON.parse(document.getElementById("allowMetricsToggling").textContent)
const displayLeaderboardDateButton = JSON.parse(document.getElementById("displayLeaderboardDateButton").textContent)

const observableDetailEditURL = JSON.parse(document.getElementById("observableDetailEditURL").textContent)
const observableComparisonEditURL = JSON.parse(document.getElementById("observableComparisonEditURL").textContent)

let resultsTable = $('#ajaxDataTable')
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
                orderable: false,
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
        document.getElementById('compare-buttons-group').innerHTML = `
            <button type="button" id="compare-results-button" class="btn btn-secondary"
                    onclick="updateEvaluationComparisonModal()" data-toggle="modal" data-target="#observableModal"
                    disabled title="${SELECT_TEXT}">
                <i class="fas fa-balance-scale-right"></i>
            </button>
        `;

        document.getElementById('compareEvaluationsHeader').innerHTML = `
            <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="Deselect all results">
                <input type="checkbox" id="compareAllEvaluationsCheckbox"/>
            </span>
        `;

        let compareAllEvaluationsCheckbox = $('#compareAllEvaluationsCheckbox')
        compareAllEvaluationsCheckbox.prop('indeterminate', true).hide()

        // On click on General checkbox
        compareAllEvaluationsCheckbox.on("click", function () {
            compareAllEvaluationsCheckbox.hide()
            selectedResults = {};
            $(`.compareEvaluationCheckbox`).prop("checked", false)
            $('#compare-results-button').prop("disabled", true).prop("title", SELECT_TEXT)
            $('#compare-warning-alert').addClass("d-none");
        })

        // On click on the table checkboxes
        resultsTable.on('click', function (e) {
            if ($(e.target).is(':checkbox')) {
                const resultId = $(e.target).val()
                const compareResultsButton = $("#compare-results-button")

                // Add or remove data to the object
                if ($(e.target).is(':checked')) {
                    selectedResults[resultId] = true
                    compareAllEvaluationsCheckbox.prop('indeterminate', true).show()
                } else {
                    delete selectedResults[resultId];
                }

                const numSelectedResults = Object.entries(selectedResults).length

                // Modify compare results button
                if (numSelectedResults > 1) {
                    compareResultsButton.prop("disabled", false)
                        .prop("title", `Compare ${numSelectedResults} results`)
                } else {
                    compareResultsButton.prop("disabled", true)
                        .prop("title", SELECT_TEXT)
                }

                if (numSelectedResults === 0) {
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

    if (allowEvaluationNavigation === true) {
        document.getElementById('compare-buttons-group').innerHTML += `
            <button type="button" id="browse-evaluations-button" class="btn btn-secondary"
                    onclick="updateEvaluationNavigationModal()" data-toggle="modal" data-target="#observableModal"
                    title="Browse through these results">
                <i class="fas fa-chart-bar"></i>
            </button>
        `;
    }

    if (displayLeaderboardDateButton === true) {
        document.getElementById('compare-buttons-group').innerHTML += `
            <button type="button" class="btn btn-secondary" data-toggle="modal" data-target="#leaderboardDateModal"
                    title="Leaderboard history">
                <i class="fas fa-history"></i>
            </button>
        `;
    }
});

$(window).resize(function () {
    resultsTable.DataTable().columns.adjust()
});

function updateEvaluationComparisonModal() {
    const search = new URLSearchParams(Object.keys(selectedResults).map(pk => ["pk", pk]))
    const notebook = document.getElementById('observableNotebook')
    const modelLabel = document.getElementById('observableModalLabel')

    modelLabel.textContent = "Compare Results"
    notebook.src = `${observableComparisonURL}?${search.toString()}`;

    const observableEditLink = document.getElementById("observableEditLink")
    if (observableEditLink !== null) {
        observableEditLink.href = `${observableComparisonEditURL}?${search.toString()}`;
    }
}

function updateEvaluationNavigationModal() {
    const pkElements = Array.from(document.getElementsByClassName("browseEvaluationPK"))
    const search = new URLSearchParams(pkElements.map(e => ["pk", e.value]))
    const notebook = document.getElementById('observableNotebook')
    const modelLabel = document.getElementById('observableModalLabel')

    modelLabel.textContent = "Browse Results"
    notebook.src = `${observableDetailURL}?${search.toString()}`;

    const observableEditLink = document.getElementById("observableEditLink")
    if (observableEditLink !== null) {
        observableEditLink.href = `${observableDetailEditURL}?${search.toString()}`;
    }
}

function getDataTablesDOMTemplate() {
    let DOM = "<'row'<'col-12'f>>"

    if (allowMetricsToggling === true || allowEvaluationComparison === true || allowEvaluationNavigation === true || displayLeaderboardDateButton === true) {
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
    if (allowEvaluationNavigation === true) {
        document.getElementById("browse-evaluations-button").disabled = document.getElementsByClassName("browseEvaluationPK").length === 0;
    }

    $(".compareEvaluationCheckbox").filter(function () {
        return $(this).attr("value") in selectedResults
    }).prop('checked', true);
}
