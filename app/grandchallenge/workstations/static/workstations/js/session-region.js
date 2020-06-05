function setModalLoadingMessage(msg) {
    document.getElementById("sessionStateMsg").textContent = msg;
}

function ping(url) {
    let errored = false;

    // First try establishes TLS
    $.ajax({
        url: url,
        async: false,
        cache: false,
        success: () => {
        },
        error: () => {
            errored = true;
        }
    });

    if (errored === true) {
        return Infinity;
    }

    let end = null;
    const start = performance.now();

    $.ajax({
        url: url,
        async: false,
        cache: false,
        success: () => {
            end = performance.now();
        },
        error: (error) => {
            console.log(error);
            end = null;
        }
    });

    if (end === null) {
        return Infinity;
    } else {
        return end - start;
    }
}

function ping_regions(regions, endpoint) {
    return regions.map(region => {
        return {"id": region.value, "ping": ping(`https://${region.value}.${endpoint}`)};
    });
}

$(document).ready(function () {
    const session_modal = $("#sessionModal");

    session_modal.modal({show: true});

    const ping_endpoint = JSON.parse(document.getElementById("ping-endpoint-data").textContent);
    const region_selection = document.getElementById("id_region");
    const ping_widget = document.getElementById("id_ping_times");
    const regions = [...region_selection.options];

    let timings = ping_regions(regions, ping_endpoint);

    ping_widget.value = JSON.stringify(timings);

    const server = timings.reduce((prev, current) => (prev.ping < current.ping) ? prev : current);
    region_selection.value = server.id;

    setModalLoadingMessage(`Connecting to ${region_selection.value}...`);
    region_selection.form.submit();
})
