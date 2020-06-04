$(document).ready(function () {
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
        )
    )
        .then(
            response => {
                let regexp = /^https:\/\/([\w-]+).*/;
                let m = response.url.match(regexp);

                if (m !== undefined) {
                    region_selection.value = m[1];

                    console.log(`Selected ${m[1]}`);

                    // region_selection.form.submit();
                }
            }
        )
        .catch(
            // Nothing resolved
            error => console.log(error)
        );
})
