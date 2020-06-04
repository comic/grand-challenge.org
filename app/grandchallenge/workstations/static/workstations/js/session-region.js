function setModalLoadingMessage(msg) {
    document.getElementById("sessionStateMsg").innerHTML = msg;
}

$(document).ready(function () {
    const session_modal = $("#sessionModal");

    session_modal.modal({show: true});

    const ping_endpoint = JSON.parse(document.getElementById("ping-endpoint-data").textContent);
    const region_selection = document.getElementById("id_region");
    const urls = [...region_selection.options].map(function (o) {
        return `https://${o.value}.${ping_endpoint}`
    });

    Promise.race(
        urls.map(
            u => fetch(u)
                .then(
                    response => {
                        return response.ok ? response : Promise.reject(response)
                    }
                )
                .catch(
                    // Nothing resolved
                    error => console.log(error)
                )
        )
    )
        .then(
            response => {
                if (response !== undefined) {
                    // If we have a match, find out what server this is for
                    let regexp = /^https:\/\/([\w-]+).*/;
                    let m = response.url.match(regexp);

                    if (m !== undefined) {
                        region_selection.value = m[1];
                    }
                }

                setModalLoadingMessage(`Connecting to ${region_selection.value}...`);
                region_selection.form.submit();
            }
        )
})
