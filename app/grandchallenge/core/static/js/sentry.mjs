const sentryDSN = JSON.parse(document.getElementById('sentryDSN').textContent);
const commitID = JSON.parse(document.getElementById('commitID').textContent);

Sentry.init({dsn: sentryDSN, release: commitID});
