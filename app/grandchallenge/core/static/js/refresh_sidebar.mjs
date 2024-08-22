$(document).ready(() => {
    const tabSelectors = $("#v-pills-tab a");

    const allowedHashes = new Set(
        tabSelectors
            .map(function () {
                const href = this.getAttribute("href");
                return href.startsWith("#") ? href : null;
            })
            .get()
            .filter(hash => hash !== null),
    );

    function isValidHash(hash) {
        return allowedHashes.has(hash);
    }

    function activateLocation() {
        const hash = window.location.hash;
        if (isValidHash(hash)) {
            const tab = $(`#v-pills-tab a[href="${hash}"]`);
            tab.siblings().removeClass("active");
            tab.tab("show");
        } else {
            // Fallback to a default tab if the hash is not valid
            const defaultTab = $('#v-pills-tab a[href="#information"]');
            defaultTab.siblings().removeClass("active");
            defaultTab.tab("show");
        }
    }

    tabSelectors.click(function () {
        const hash = $(this).attr("href");
        if (isValidHash(hash)) {
            history.pushState(null, null, hash);
            activateLocation();
        }
    });

    window.addEventListener("popstate", event => {
        activateLocation();
    });

    window.addEventListener("pageshow", event => {
        activateLocation();
    });

    activateLocation();
});
