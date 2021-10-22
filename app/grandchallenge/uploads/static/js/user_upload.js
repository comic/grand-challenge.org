"use strict";

{
    document.addEventListener("DOMContentLoaded", () => {
        const widgets = document.getElementsByClassName("user-upload");
        for (const widget of widgets) {
            initializeWidget(widget)
        }
    });

    function initializeWidget(widget) {
        const inputId = widget.getAttribute("data-input-id");
        const inputName = widget.getAttribute("data-input-name");
        const multiWidget = widget.getAttribute("data-multiple");
        const allowedFileTypes = JSON.parse(document.getElementById(`${inputId}AllowedFileTypes`).textContent);

        let uppy = new Uppy.Core({
            id: `${window.location.pathname}-${inputId}`,
            autoProceed: true,
            restrictions: { allowedFileTypes },
        });

        uppy.on('restriction-failed', (file, error) => {
            window.alert(`Could not upload ${file.name} (${file.type}): ${error.message}`);
        })

        uppy.use(Uppy.DragDrop, {
            target: `#${inputId}-drag-drop`,
        });

        uppy.use(Uppy.StatusBar, {
            target: `#${inputId}-progress`,
            showProgressDetails: true,
            hideCancelButton: true,
            hidePauseResumeButton: true,
        });

        uppy.use(Uppy.AwsS3Multipart, {
            getChunkSize: () => 20 * 1024 * 1024,
            createMultipartUpload: createMultipartUpload,
            listParts: listParts,
            prepareUploadParts: prepareUploadParts,
            abortMultipartUpload: abortMultipartUpload,
            completeMultipartUpload: completeMultipartUpload,
        });

        uppy.on("upload-success", (file, response) => {
            const uploadedPK = file.s3Multipart.key.split("/")[2];
            const fileList = document.getElementById(`${inputId}-file-list`);

            if (multiWidget === null) {
                fileList.innerHTML = "";

                document.getElementById(inputId).value = uploadedPK
            } else {
                let noFilesWarning = document.getElementById(`${inputId}-no-files-warning`);
                if (noFilesWarning !== null) { noFilesWarning.outerHTML = ""; }

                let input = document.createElement("input");
                input.name = inputName;
                input.type = "hidden";
                input.value = uploadedPK;
                widget.appendChild(input);
            }

            let newIcon = document.createElement("i");
            newIcon.classList.add("fas","fa-check","fa-fw","text-success");
            newIcon.setAttribute("title", "File Successfully Uploaded");

            let newFile = document.createElement("li");
            newFile.classList.add("list-group-item");
            newFile.appendChild(newIcon);
            newFile.insertAdjacentText( "beforeend",` ${uploadedPK} (${file.name})`);
            fileList.prepend(newFile);
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getPOSTParams() {
        return {
            uploadListView: JSON.parse(document.getElementById("uploadListView").textContent),
            csrfToken: getCookie("_csrftoken"),
        };
    }

    function createMultipartUpload(file) {
        const postParams = getPOSTParams();

        return fetch(
            postParams.uploadListView,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken,
                },
                body: JSON.stringify({"filename": file.name})
            }
        ).then(response => response.json()
        ).then(upload => ({
            uploadId: upload.s3_upload_id,
            key: upload.key,
        }))
    }

    function listParts(file, {uploadId, key}) {
        const postParams = getPOSTParams();
        const uploadPK = key.split("/")[2];

        return fetch(
            `${postParams.uploadListView}${uploadPK}/${uploadId}/list-parts/`,
            {
                method: "GET",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken,
                }
            }
        ).then(response => response.json()
        ).then(upload => upload.parts)
    }

    class FetchError extends Error {}

    function prepareUploadParts(file, {uploadId, key, partNumbers}) {
        const postParams = getPOSTParams();
        const uploadPK = key.split("/")[2];

        return fetch(
            `${postParams.uploadListView}${uploadPK}/${uploadId}/generate-presigned-urls/`,
            {
                method: "PATCH",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken,
                },
                body: JSON.stringify({
                    "part_numbers": partNumbers,
                })
            }
        ).then(response => {
            if (response.ok) {
                return response.json();
            } else {
                if (response.status === 403) {
                    response.json().then(err => window.alert(err.detail));
                }
                throw new FetchError(response.status.toString());
            }
        }).then(upload => ({presignedUrls: upload.presigned_urls})
        ).catch(e => {
            console.error(e);
            if (e instanceof FetchError || e.name === "TypeError") {
                // Catches FetchError defined above or TypeError (= network error thrown
                // by fetch) and makes uppy retry. Will not catch SyntaxError caused by
                // invalid JSON.
                const status = e instanceof FetchError ? parseInt(e.message) : 0;
                return Promise.reject({ source: { status: status } });
            }
            throw e;
        });
    }

    function abortMultipartUpload(file, {uploadId, key}) {
        const postParams = getPOSTParams();
        const uploadPK = key.split("/")[2];

        return fetch(
            `${postParams.uploadListView}${uploadPK}/${uploadId}/abort-multipart-upload/`,
            {
                method: "PATCH",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken,
                },
            }
        )
    }

    function completeMultipartUpload(file, {uploadId, key, parts}) {
        const postParams = getPOSTParams();
        const uploadPK = key.split("/")[2];

        return fetch(
            `${postParams.uploadListView}${uploadPK}/${uploadId}/complete-multipart-upload/`,
            {
                method: "PATCH",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken,
                },
                body: JSON.stringify({"parts": parts})
            }
        )
    }
}
