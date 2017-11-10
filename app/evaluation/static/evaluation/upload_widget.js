"use strict";

var upload_csrf_token;

(function () {
    var csrf_token = null;

    function fold_unfold(element) {
        // Find the parent-foldable element
        element = $(element);
        while (!element.hasClass("foldable")) {
            element = element.parent();
            if (element.length == 0) {
                throw Error("No parent element with class 'foldable' found");
            }
        }
        element.toggleClass("folded");
    }

    function init_upload(upload_element) {
        upload_element = $(upload_element);
        var dropzone = upload_element;
        var failed_files_list = upload_element.find("div.failed-list");

        var target_url = upload_element.attr("upload_target");

        upload_element.fileupload(
            {
                url: target_url,
                dropZone: dropzone,
                headers: {
                    "X-CSRFToken": csrf_token
                }
            });

        var drop_overlay_timer = null;
        var drop_here_floater = upload_element.find(".drop-here-floater");

        function show_drop_overlay() {
            if (drop_overlay_timer !== null) {
                clearTimeout(drop_overlay_timer);
                drop_overlay_timer = null;
            } else {
                drop_here_floater.css("display", "block");
            }
            drop_overlay_timer = setTimeout(hide_drop_overlay, 2000000);
        }

        function hide_drop_overlay() {
            if (drop_overlay_timer !== null) {
                clearTimeout(drop_overlay_timer);
                drop_overlay_timer = null;
            }
            drop_here_floater.css("display", "none");
        }

        dropzone.on('dragover', function (e) {
            show_drop_overlay();
        });
        drop_here_floater.on('dragleave', function (e) {
            console.log("dragleave");
            hide_drop_overlay();
        });
        drop_here_floater.on('dragexit', function (e) {
            console.log("dragexit");
            hide_drop_overlay();
        });
        drop_here_floater.on('drop', function (e) {
            hide_drop_overlay();
        });

        failed_files_list.find("button.remove").on("click", function (element) {
            failed_files_list.css("display", "none");
            failed_files_list.addClass("folded");
            failed_files_list.find("span.count").text("0");
            failed_files_list.find("div.failed-upload").remove();
        });

        function add_failed_upload(filename, message) {
            failed_files_list.css("display", "block");
            var countSpan = failed_files_list.find("span.count");
            countSpan.text("" + (parseInt(countSpan.text(), 10) + 1));
            failed_files_list.append($("<div class='failed-upload'><p><span class='left'>" + filename + "</span>" + message + "</p></div>"));
        }
    }

    $(function () {
        if (typeof upload_csrf_token !== 'undefined') {
            csrf_token = upload_csrf_token;
        } else {
            // Try to find a django-hidden control with the correct value
            var elements = $("input[name='csrfmiddlewaretoken']");
            if (elements.length > 0) {
                csrf_token = elements.attr("value");
            }
        }

        if (!csrf_token) {
            throw Error("Could not find a CSRF token, the uploads will not work!");
        } else {
            var file_uploads = $(".file-upload");
            for (var i = 0; i < file_uploads.length; i++) {
                init_upload(file_uploads[i]);
            }
        }
    });
})();
