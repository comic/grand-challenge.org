"use strict";

(function () {
    function init_upload(upload_element) {
        upload_element = $(upload_element);
        var dropzone = upload_element;
        var retry_counts = {};
        var form_element = upload_element.find("input[type='hidden']");
        var failed_files_list = upload_element.find("div.failed-list");
        var total_expected_files = 0;

        var is_multiupload = upload_element.data("multi-upload");
        var is_autocommit = upload_element.data("auto-commit");
        var target_url = upload_element.data("upload-target");
        var file_size_url = upload_element.data("file-size-url");
        var auth_token = upload_element.data("auth-token");

        var client_upload_session_key = generate_labeled_id("client_upload_session");
        target_url = target_url + "?client_session=" + client_upload_session_key;

        function generate_labeled_id(label) {
            var rnd = "" + Math.floor(Math.random() * 1000000);
            var date = (new Date).toISOString();
            var filename = label.slice(0, 32);
            return filename + '_' + rnd + '_' + date;
        }

        upload_element.fileupload(
            {
                url: target_url,
                dropZone: dropzone,
                maxChunkSize: 8000000,
                retryTimeout: 500,
                maxRetries: 50,
                headers: {
                    "Authorization": "Token " + auth_token
                },
                limitConcurrentUploads: 3,
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
            hide_drop_overlay();
        });
        drop_here_floater.on('dragexit', function (e) {
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
            failed_files_list.append(
                $("<div id='" + filename.replace('.', '-') + "' class='failed-upload'><p><span class='left'>" + filename + "</span>" + message + "</p></div>"));
        }

        function generate_uploaded_file_element(filename, uuid, extra_attributes) {
            return $("<div class='uploaded-file'>Uploaded: " + filename + "</div>")
        }

        var succeeded_uploads_list = [];

        function clear_succeeded_list() {
            succeeded_uploads_list = [];
            upload_element.find("div.uploaded-file").remove();
            update_hidden_form_element();
        }

        function add_succeeded_upload(file_info_list) {
            for (var i = 0; i < file_info_list.length; i++) {
                var file_info = file_info_list[i];
                failed_files_list.find("#" + file_info.filename.replace('.', '-')).remove();
                upload_element.append(
                    generate_uploaded_file_element(
                        file_info.filename,
                        file_info.uuid,
                        file_info.extra_attrs
                    )
                );
                succeeded_uploads_list.push(file_info);
            }
            update_hidden_form_element();

            if (is_autocommit &&
                (succeeded_uploads_list.length === total_expected_files)) {
                total_expected_files = 0; // In case we submit does not work
                upload_element.closest('form').submit();
            }
        }

        function update_hidden_form_element() {
            var uuid_list_string = "";
            for (var i = 0; i < succeeded_uploads_list.length; i++) {
                if (uuid_list_string !== "") {
                    uuid_list_string += ",";
                }
                uuid_list_string += succeeded_uploads_list[i].uuid;
            }
            form_element.val(uuid_list_string);
        }

        var fileinput_button = upload_element.find("span.fileinput-button");
        var progress_div = upload_element.find("div.progress");

        upload_element.on('fileuploadadd', function (e, data) {
            if (!is_multiupload) {
                fileinput_button.css("display", "none");
            }
            progress_div.removeClass("d-none");
            total_expected_files += data.files.length;
        });

        upload_element.on('fileuploadsubmit', function (e, data) {
            if (!data.formData || !data.formData["X-Upload-ID"]) {
                data.formData = {
                    "X-Upload-ID": generate_labeled_id(data.files[0].name)
                };
            }
        });

        var progress_bar = progress_div.find(".progress-bar");

        upload_element.on('fileuploaddone', function (e, data) {
            if (!is_multiupload) {
                clear_succeeded_list();
            }
            add_succeeded_upload(data.result);
        });

        upload_element.on('fileuploadfail', function (e, data) {
            var file = data.files[0];
            // This is a failed chunk and gets handled seprately.
            if (file.size > data.maxChunkSize) {
                return
            }
            if (!is_multiupload) {
                clear_succeeded_list();
            }
            var error_message = "Sending failed.";
            var response = data.response();
            if (response && response.jqXHR && response.jqXHR.responseJSON) {
                error_message = response.jqXHR.responseJSON[0];
            }

            for (var i = 0; i < data.files.length; i++) {
                var file = data.files[i];
                data.loaded -= file.size;
                add_failed_upload(file.name, error_message);
            }
            data.data = null;
            data.submit();
        });

        upload_element.on('fileuploadchunkfail', function (e, data) {
            var fu = $(this).data('blueimp-fileupload') || $(this).data('fileupload');
            var retries = retry_counts[data.files[0].name] || 0;
            var retry = function () {
                $.getJSON(file_size_url, {file: data.formData["X-Upload-ID"]})
                    .done(function (result) {
                        // Add 1 to the size, because we want the upload the resume
                        // on the next byte (for some reasen jq fileupload does not
                        // do so).
                        data.uploadedBytes = result.current_size + 1;
                        // clear the previous data:
                        data.data = null;
                        data.submit();
                    })
            };
            if (data.errorThrown !== 'abort' &&
                data.uploadedBytes < data.files[0].size &&
                retries < fu.options.maxRetries) {
                    retries += 1;
                    retry_counts[data.files[0].name] = retries;
                    window.setTimeout(retry, retries * fu.options.retryTimeout);
                    return;
            }
            delete retry_counts[data.files[0].name];
            $.blueimp.fileupload.prototype.options.fail.call(this, e, data);
            });


        upload_element.on('fileuploadprogressall', function (e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            progress_bar.css(
                'width',
                progress + '%'
            );
            var failed_files = failed_files_list.find('div.failed-upload').length > 0;
            progress_bar.toggleClass("bg-info progress-bar-striped progress-bar-animated", !failed_files).toggleClass('bg-danger', failed_files);

            if (progress >= 100) {
                progress_bar.removeClass("bg-info progress-bar-striped progress-bar-animated bg-danger").addClass("bg-success");
            }

        });
    }

    $(function () {
        var file_uploads = $(".file-upload");
        for (var i = 0; i < file_uploads.length; i++) {
            init_upload(file_uploads[i]);
        }
    });
})();
