deleteGroundTruth = () => {
    $.ajax({
        url: JSON.parse(document.getElementById("removeUrl").textContent),
        type: "POST",
        complete: () => {location.reload()},
        headers: {
            'X-CSRFToken': window.drf.csrftoken,
            'Content-Type': 'application/json'
        },
    });
};
