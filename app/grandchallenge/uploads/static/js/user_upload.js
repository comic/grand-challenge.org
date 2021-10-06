"use strict";

(function () {
    document.addEventListener("DOMContentLoaded", function (event) {
        const widgets = document.getElementsByClassName("user-upload");
        for (const widget of widgets) {
            initializeWidget(widget)
        }
    });

    function initializeWidget(widget) {
        const inputId = widget.getAttribute("data-inputId");

        let uppy = new Uppy.Core().use(Uppy.Dashboard, {
            inline: true,
            target: `#${inputId}-drag-drop`
        }).use(Uppy.AwsS3Multipart, {
            getChunkSize: (file) => {
                return 20 * 1024 * 1024
            },
            createMultipartUpload: createMultipartUpload,
            listParts: listParts,
            prepareUploadParts: prepareUploadParts,
            abortMultipartUpload: abortMultipartUpload,
            completeMultipartUpload: completeMultipartUpload
        })

        uppy.on('complete', (result) => {
            console.log('Upload complete! We’ve uploaded these files:', result.successful)
        })
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
            apiRoot: JSON.parse(document.getElementById("apiRoot").textContent),
            csrfToken: getCookie("_csrftoken")
        };
    }

    function createMultipartUpload(file) {
        const postParams = getPOSTParams();

        return fetch(
            `${postParams.apiRoot}uploads/`,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken
                },
                body: JSON.stringify({
                    "filename": file.name
                })
            }
        ).then(response => response.json()
        ).then(upload => {
            return {
                uploadId: upload.s3_upload_id,
                key: upload.key
            }
        })
    }

    function listParts(file, {uploadId, key}) {
        const postParams = getPOSTParams();

        return fetch(
            `${postParams.apiRoot}${key}/${uploadId}/list-parts/`,
            {
                method: "GET",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken
                }
            }
        ).then(response => response.json()
        ).then(upload => {
            return upload.parts
        })
    }

    function prepareUploadParts(file, {uploadId, key, partNumbers}) {
        const postParams = getPOSTParams();

        return fetch(
            `${postParams.apiRoot}${key}/${uploadId}/generate-presigned-urls/`,
            {
                method: "PATCH",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken
                },
                body: JSON.stringify({
                    "part_numbers": partNumbers
                })
            }
        ).then(response => response.json()
        ).then(upload => {
            return {
                presignedUrls: upload.presigned_urls
            }
        })
    }

    function abortMultipartUpload(file, {uploadId, key}) {
        const postParams = getPOSTParams();

        return fetch(
            `${postParams.apiRoot}${key}/${uploadId}/abort-multipart-upload/`,
            {
                method: "PATCH",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken
                },
            }
        )
    }

    function completeMultipartUpload(file, {uploadId, key, parts}) {
        const postParams = getPOSTParams();

        return fetch(
            `${postParams.apiRoot}${key}/${uploadId}/complete-multipart-upload/`,
            {
                method: "PATCH",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": postParams.csrfToken
                },
                body: JSON.stringify({
                    "parts": parts
                })
            }
        )
    }
})();
