$(document).ready(() => {
    let unsaved = false;

    $(":input").change(() => {
        unsaved = true;
    });

    $("#submit-id-save").click(() => {
        unsaved = false;
    });

    function unloadPage() {
        if (unsaved) {
            return "You have unsaved changes on this page. Do you want to leave this page and discard your changes or stay on this page?";
        }
    }

    window.onbeforeunload = unloadPage;
});
