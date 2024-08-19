$(document).ready(function () {
    var unsaved = false;

    $(":input").change(function () {
        unsaved = true;
    });

    $('#submit-id-save').click(function() {
        unsaved = false;
    });

    function unloadPage() {
        if (unsaved) {
            return "You have unsaved changes on this page. Do you want to leave this page and discard your changes or stay on this page?";
        }
    }

    window.onbeforeunload = unloadPage;
});
