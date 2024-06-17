$(document).ready(function() {
    const tabSelectors = $('#v-pills-tab a');

    const allowedHashes = new Set(
        tabSelectors.map(function() {
            let href = this.getAttribute('href');
            return href.startsWith('#') ? href.substring(1) : null;
        }).get().filter(hash => hash !== null)
    );

    function isValidHash(hash) {
        return allowedHashes.has(hash);
    }

    tabSelectors.click(function () {
        const tab = $(this);
        tab.siblings().removeClass('active');
        tab.tab('show');
    });

    $("ul.nav-pills > a").on("shown.bs.tab", (e) => {
        const hash = $(e.target).attr("href").substring(1);
        if (isValidHash(hash)) {
            history.pushState(null, null, `#${hash}`);
        }
    });

    function activateLocation() {
        const hash = window.location.hash.substring(1);
        if (isValidHash(hash)) {
            const tab = $(`#v-pills-tab a[href="#${hash}"]`);
            tab.siblings().removeClass('active');
            tab.tab('show');
        } else {
            // Fallback to a default tab if the hash is not valid
            const defaultTab = $('#v-pills-tab a[href="#information"]');
            defaultTab.siblings().removeClass('active');
            defaultTab.tab('show');
        }
    }

    window.addEventListener('popstate', function (event) {
        activateLocation();
    });

    window.addEventListener('pageshow', function(event) {
        activateLocation();
    });

    activateLocation();
});
