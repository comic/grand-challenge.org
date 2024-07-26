function renderVegaLiteChart(element) {
    const spec = JSON.parse(element.children[0].textContent);
    vegaEmbed(element, spec);
    setTimeout(() => window.dispatchEvent(new Event("resize")), 1);
}

document.addEventListener("DOMContentLoaded", function(event) {
    for (const element of document.getElementsByClassName("vega-lite-chart")) {
        renderVegaLiteChart(element);
    }
});


// Lazy rendering
// Tag the containers with the class 'vega-lite-chart-lazy' to only render
const handledAttribute = "data-vega-chart-is-rendered";

function handleInterSection(entries) {
    entries.forEach((entry) => {
        if (entry.intersectionRatio < 0.40) {
            return;
        }

        const element = entry.target;


        if (element.getAttribute(handledAttribute)) {
            return;
        }

        renderVegaLiteChart(element);

        // Tag the element as being handled
        element.setAttribute(handledAttribute, "");
        this.unobserve(element);
        }
    )
}

const observer = new IntersectionObserver(handleInterSection, {
  rootMargin: "0px",
  threshold: 1.0,
});


document.addEventListener("DOMContentLoaded", function(event) {
    for (const element of document.getElementsByClassName("vega-lite-chart-lazy")) {
        observer.observe(element, );
    }
});
