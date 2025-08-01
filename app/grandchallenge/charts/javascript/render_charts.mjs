import vegaEmbed from "vega-embed";

function renderVegaLiteChart(element) {
    const spec = JSON.parse(element.children[0].textContent);
    vegaEmbed(element, spec);
}

// Elements with the class "vega-lite-chart" will only be rendered when they are in the viewport
// The element will be tagged with the attribute "data-vega-chart-is-rendered" to prevent re-rendering
const handledAttribute = "data-vega-chart-is-rendered";

function handleInterSection(entries) {
    for (const entry of entries) {
        if (entry.intersectionRatio < 0.4) {
            return;
        }

        const element = entry.target;

        if (element.getAttribute(handledAttribute)) {
            return;
        }

        renderVegaLiteChart(element);

        // Tag the element as being handled
        element.setAttribute(handledAttribute, "true");
        this.unobserve(element);
    }
}

const observer = new IntersectionObserver(handleInterSection, {
    rootMargin: "0px",
    threshold: 1.0,
});

document.addEventListener("DOMContentLoaded", event => {
    for (const element of document.getElementsByClassName("vega-lite-chart")) {
        observer.observe(element);
    }
});

function renderVegaChartsInAddedNodes(mutationList, observer) {
    for (const mutation of mutationList) {
        for (const addedNode of mutation.addedNodes) {
            if (addedNode.nodeType !== Node.TEXT_NODE) {
                for (const element of addedNode.getElementsByClassName(
                    "vega-lite-chart",
                )) {
                    if (!element.getAttribute(handledAttribute)) {
                        renderVegaLiteChart(element);
                        element.setAttribute(handledAttribute, "true");
                    }
                }
            }
        }
    }
}

const renderVegaChartsObserver = new MutationObserver(
    renderVegaChartsInAddedNodes,
);

export { renderVegaChartsObserver };
