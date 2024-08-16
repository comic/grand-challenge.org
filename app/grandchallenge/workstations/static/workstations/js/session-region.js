function setModalLoadingMessage(msg) {
  document.getElementById("sessionStateMsg").textContent = msg;
}

function ping(url) {
  // First try establishes TLS
  let errored = false;
  $.ajax({
    url: url,
    async: false,
    cache: false,
    success: () => {},
    error: () => {
      errored = true;
    },
  });

  if (errored === true) {
    return Infinity;
  }

  // Now measure the response time
  let end = Infinity;
  const start = performance.now();
  $.ajax({
    url: url,
    async: false,
    cache: false,
    success: () => {
      end = performance.now();
    },
    error: () => {},
  });

  return end - start;
}

function ping_regions(regions, endpoint) {
  return regions.map((region) => {
    return {
      id: region.value,
      ping: ping(`https://${region.value}.${endpoint}`),
    };
  });
}

$(document).ready(function () {
  const session_modal = $("#sessionModal");

  session_modal.on("shown.bs.modal", function () {
    const ping_endpoint = JSON.parse(
      document.getElementById("ping-endpoint-data").textContent,
    );
    const region_selection = document.getElementById("id_region");
    const ping_widget = document.getElementById("id_ping_times");
    const regions = [...region_selection.options];

    let timings = ping_regions(regions, ping_endpoint);

    ping_widget.value = JSON.stringify(timings);

    const server = timings.reduce((prev, current) =>
      prev.ping < current.ping ? prev : current,
    );
    region_selection.value = server.id;

    setModalLoadingMessage(`Connecting to ${region_selection.value}...`);
    region_selection.form.submit();
  });

  session_modal.modal({ show: true });
});
