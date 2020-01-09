$(document).ready(function () {

    // use this to no use any fancy effects no first load of page.
    // hide fancy effect because this looks stupid
    var FIRST_LOAD = true;

    //the class that a projectlink always has. Used as selector to get all
    //projectlinks
    var BASE_SELECTOR = "projectlink";

    var filterbuttons = $("#projectfilterbuttons input");

    init();

    function init() {
        // hook up each inputbox to filter items by the same name when
        // checked or unchecked

        filterbuttons.each(function (i, d) {
            log("hooking ." + d.id);
            hookFilter(d.id);
        });

        updateTotalCounter();
        updateAll();

    }

    function updateTotalCounter() {
        //Write the total number of projectlinks, invisible or visible, into
        //a span with class 'counter' and id 'total'

        var count = $("div." + BASE_SELECTOR).length;
        $("#counter-total").html(count)

    }

    function hookFilter(inputname) {
        // hook up the checkbox with id inputname so that checking it will
        // hide or show projectlink items with a class by the same name
        var label = $("label#" + inputname);
        $("input#" + inputname).click(function () {
            updateAll();
        });
        //add a counter to show number of elements displayed next to label
        label.append("<span class ='itemCount' id = '" + inputname + "'></span>")

    }


    function updateAll() {
        //make sure what is shown is consistant with the state of the tickboxes
        log("update: first load is now " + FIRST_LOAD);
        var fadetime = 400;
        if (FIRST_LOAD) {
            fadetime = 0;
        }
        //Make sure items shown correspond to checkboxes
        log("Refreshing all links");
        var projectlinks = {"show": $(), "hide": $()};

        var active_filters = [];

        filterbuttons.each(function (i, d) {
            log("updating according to " + d.id);
            var checkbox = $(d);
            if (checkbox.attr("class") === "filter form-check-input" && checkbox.is(':checked')) {
                active_filters.push(checkbox);
            }
            projectlinks = modifyCollection(checkbox, projectlinks)
        });

        //Update active filters and counter visualization
        $('#active_filter_count').text(active_filters.length);
        $('#all_active_filters').empty();
        active_filters.forEach(function (checkbox) {
            var close_icon = $('<i>', {'class': 'fas fa-times'});
            var text = $('<span>', {'class': 'filter-text'}).text(" " + checkbox.val());
            var filter_tag = $('<button>', {'class': 'btn btn-outline-info btn-sm'});

            filter_tag.append(close_icon).append(text);
            filter_tag.click(function () {
                checkbox.prop('checked', false);
                updateAll();
            });

            $('#all_active_filters').append(filter_tag);
        });

        var reset_button = $('#btn_reset_filters');

        if (active_filters.length > 0) {
            reset_button.show();
        } else {
            reset_button.hide();
        }


        //after collection all modifications, apply these
        var show = projectlinks["show"];
        var hide = projectlinks["hide"];
        show = removeDuplicates(show, hide);


        //after fading or hiding, update counters once.
        $.when(show.show(fadetime)).then(function () {
            update();
        });

        $.when(hide.hide(fadetime)).then(function () {
            update();
        });

        // allow fancy effects after this
        FIRST_LOAD = false;
    }

    function update() {
        updateCounters();
        updateLabels();
    }


    function modifyCollection(checkbox, collection) {
        // Make sure the collection of link items is consistent with
        // the value of checkbox. This means add or remove items with same id
        // as checkbox based on it being checked or not

        var show = collection["show"];
        var hide = collection["hide"];
        if (show === undefined || hide === undefined) {
            log("WARNING: input collections needs to be a dict with two elements, 'show' and 'hide', one of these was not found. Returning input collection unchanged");
        }


        var name = checkbox.attr("id");
        if (name === "") {
            log("WARNING: checkbox " + checkbox + " did not have an id, I need this to do filtering. Return input collection unchanged.");
            return collection;
        }

        if (checkbox.attr("class") === "filter form-check-input") {
            //filter checkbox will remove all others when checked
            if (checkbox.is(':checked')) {
                log("hiding all non '." + name + "'");
                hide = hide.add(".projectlink:not(." + name + ")");
            } else {
                log("filter on '." + name + "' released. doing nothing.");
            }

        } else if (checkbox.attr("class") === "include") {
            // include checkbox will include or exclude only the items with
            // the same name
            if (checkbox.is(':checked')) {
                log("showing ''." + name + "'");
                show = show.add(".projectlink." + name);

            } else {
                log("hiding '." + name + "'");
                hide = hide.add(".projectlink." + name);
            }

        } else {
            log("WARNING, checkbox having class " + checkbox.attr("class") + " did not have a known class. I don't know what to do when this box is checked")
        }
        collection = {"show": show, "hide": hide};
        return collection;
    }


    function updateCounters() {
        // update counters showing how many projectlinks are currently shown
        // for each category

        filterbuttons.each(function (i, d) {
            log("updating counters for " + d.id);
            var inputname = d.id;
            var count = $("div." + inputname + ":visible").length;
            $("span.counter#" + inputname).html(count)
        })
    }

    function updateLabels() {
        // Grey out labels for include buttons when not selected, because it
        // makes the most sense given their function

        filterbuttons.each(function (i, d) {
            log("updating labels for " + d.id);
            var inputname = d.id;
            if ($(d).is(':checked')) {
                $("label#" + inputname).removeClass("greyed_out")
            } else {
                $("label#" + inputname).addClass("greyed_out")
            }
        })
    }

    function removeDuplicates(collection1, collection2) {
        if (collection2 === undefined) {
            log("WARNING: input Collection2 was not given");
        }

        var filtered = $();
        //remove any element from collection1 which is also in collection2
        collection1.each(function (i, d) {
            if (collection2.index(d) === -1) {
                filtered = filtered.add(d);
            }

        });
        return filtered;
    }

    $('#btn_reset_filters').click(function () {
        log("Clicked reset filters!");
        $("#projectfilterbuttons input.filter").prop("checked", false);
        updateAll();
    });

    function log(msg) {
        var logging = false;

        if (logging) {
            console.log("* " + msg)
        }
    }

});
