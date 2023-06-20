const googleAnalyticsID = JSON.parse(document.getElementById('googleAnalyticsID').textContent);

window.dataLayer = window.dataLayer || [];

function gtag() {
    dataLayer.push(arguments);
}

gtag('js', new Date());
gtag('config', googleAnalyticsID);
