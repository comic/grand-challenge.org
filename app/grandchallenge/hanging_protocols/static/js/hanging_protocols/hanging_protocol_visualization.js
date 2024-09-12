const possibleViewPorts = JSON.parse(
    document.getElementById("possibleViewPorts").textContent,
);

function insertAfter(newNode, existingNode) {
    existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
}

function removeAllChildNodes(parent) {
    while (parent.firstChild) {
        parent.removeChild(parent.firstChild);
    }
}

function showOrHideVisualizationDiv(divId, jsonString) {
    if (jsonString !== "" && jsonString !== "null") {
        document.getElementById(divId).style.display = "block";
    } else {
        document.getElementById(divId).style.display = "none";
    }
}

function getGridDimensions(json) {
    const dims = { x: [], y: [], w: [], h: [] };

    for (const viewport of json) {
        for (const d of Object.keys(dims)) {
            if (d in viewport) {
                dims[d].push(viewport[d]);
            }
        }
    }

    const totalWidth =
        dims.x.length !== json.length || dims.w.length !== json.length
            ? json.length
            : Math.max(...dims.x.map((num, idx) => num + dims.w[idx]));
    const totalHeight =
        dims.y.length !== json.length || dims.h.length !== json.length
            ? 1
            : Math.max(...dims.y.map((num, idx) => num + dims.h[idx]));

    return [totalHeight, totalWidth];
}

function createViewportDiv(
    divId,
    viewportNum,
    viewportSpec,
    totalHeight,
    totalWidth,
    maxOrder,
) {
    const viewportDiv = document.createElement("div");
    viewportDiv.setAttribute("id", viewportSpec.viewport_name);
    if (possibleViewPorts.includes(viewportSpec.viewport_name)) {
        viewportDiv.style.background = "#7b8a8b";
    } else {
        viewportDiv.style.background = "#e74c3c";
    }
    viewportDiv.style.opacity = "0.5";
    viewportDiv.style.position = "absolute";
    viewportDiv.style.fontSize = "1.5em";
    viewportDiv.style.zIndex = (-(viewportSpec.order - maxOrder)).toFixed(0);
    viewportDiv.style.width = Number.isNaN(viewportSpec.w)
        ? `${((1 / Number.parseFloat(totalWidth)) * 100).toFixed(2)}%`
        : `${((viewportSpec.w / Number.parseFloat(totalWidth)) * 100).toFixed(2)}%`;
    viewportDiv.style.height = Number.isNaN(viewportSpec.h)
        ? "100%"
        : `${((viewportSpec.h / Number.parseFloat(totalHeight)) * 100).toFixed(2)}%`;
    viewportDiv.style.left = Number.isNaN(viewportSpec.x)
        ? `${((viewportNum / Number.parseFloat(totalWidth)) * 100).toFixed(2)}%`
        : `${((viewportSpec.x / Number.parseFloat(totalWidth)) * 100).toFixed(2)}%`;
    viewportDiv.style.top = Number.isNaN(viewportSpec.y)
        ? "0%"
        : `${((viewportSpec.y / Number.parseFloat(totalHeight)) * 100).toFixed(2)}%`;
    document
        .getElementById(divId)
        .appendChild(viewportDiv)
        .classList.add(
            "rounded",
            "border",
            "border-2",
            "d-flex",
            "flex-column",
            "justify-content-center",
            "align-items-center",
        );

    if (!possibleViewPorts.includes(viewportSpec.viewport_name)) {
        viewportDiv.innerHTML +=
            '<p class="mb-0" style="color: #fff">Invalid viewport name</p>';
    } else {
        viewportDiv.innerHTML += `<p class="mb-0">${viewportSpec.viewport_name}</p>`;
        if (viewportSpec.fullsizable) {
            viewportDiv.innerHTML += '<i class="fas fa-expand"></i>';
        }
    }
}

function updateHangingProtocolVisualization(
    parentDivId = "hpVisualization",
    jsonString = document.getElementById("id_json").value,
) {
    showOrHideVisualizationDiv(parentDivId, jsonString);
    try {
        const jsonSpec = JSON.parse(jsonString);
        const validJsonSpec = jsonSpec.filter(
            viewPort => typeof viewPort.viewport_name !== "undefined",
        );
        const [totalHeight, totalWidth] = getGridDimensions(validJsonSpec);
        const maxOrder = Math.max(...validJsonSpec.map(v => v.order));
        removeAllChildNodes(document.getElementById(parentDivId));
        for (let i = 0; i < validJsonSpec.length; i++) {
            createViewportDiv(
                parentDivId,
                i,
                validJsonSpec[i],
                totalHeight,
                totalWidth,
                maxOrder,
            );
        }
    } catch (err) {}
}
