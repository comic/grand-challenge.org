/** global: django */

window.addEventListener("load", event => {
    if (typeof django !== "undefined" && typeof django.jQuery !== "undefined") {
        ($ => {
            // add colorpicker to inlines added dynamically
            $(document).on(
                "formset:added",
                function onFormsetAdded(event, row) {
                    jscolor.install();
                },
            );
        })(django.jQuery);
    }
});
