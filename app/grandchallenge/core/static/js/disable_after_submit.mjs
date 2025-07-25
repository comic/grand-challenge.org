/**
 * @description
 * This module provides functionality to temporarily disable forms that have the
 * `gc-disable-after-submit` attribute.
 *
 * It does so by disabling all fieldsets and hence indirectly all their children.
 * In addition, it shows a spinner on all submit buttons within forms.
 *
 * This prevents duplicate form submissions.
 *
 * Fieldsets are re-enabled and spinners removed after a short timeout.
 */

// Timeout in milliseconds before re-enabling fieldsets and removing spinners.
const reEnableTimeout = 10000;

// Attribute names
const baseAttributeName = "gc-disable-after-submit";
const initAttributeName = `${baseAttributeName}-initialized`;
const disabledAttributeName = `${baseAttributeName}-disabled`;
const spinnerAttributeName = `${baseAttributeName}-spinner`;

// Holds timers for later cancelation
const formTimers = new Set();

function initDisableAfterSubmit() {
    const forms = document.querySelectorAll(`form[${baseAttributeName}]`);

    for (const form of forms) {
        if (!form.hasAttribute(initAttributeName)) {
            form.addEventListener("submit", handleFormSubmit);
            form.setAttribute(initAttributeName, "");
        }
    }
}

function handleFormSubmit(event) {
    const form = event.currentTarget;

    // Sanity: submitting a disabled form should be prevented
    if (form.hasAttribute(disabledAttributeName)) {
        event.preventDefault();
        return;
    }

    // Delay the disable so form data is actually submitted.
    // Disabled-element values are thus not excluded.
    const disableTimerId = setTimeout(disable, 0, form);
    formTimers.add(disableTimerId);
}

function disable(form) {
    if (!form) {
        // Form no longer exists.
        return;
    }

    // Sanity: ensure we don't disable something twice.
    if (form.hasAttribute(disabledAttributeName)) {
        return;
    }
    form.setAttribute(disabledAttributeName, "");

    // Disable fieldsets.
    const fieldsets = form.querySelectorAll("fieldset");
    for (const fs of fieldsets) {
        fs.disabled = true;
    }

    // Disable buttons and add a spinner
    const submitButtons = form.querySelectorAll('button[type="submit"]');
    for (const btn of submitButtons) {
        btn.disabled = true;

        const spinner = document.createElement("span");
        spinner.setAttribute(spinnerAttributeName, "");
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        spinner.className = "spinner-border spinner-border-sm mr-1";

        btn.prepend(spinner);
    }

    // Re-enable after a while to safeguard against unforeseen errors / cancelations.
    const enableTimerId = setTimeout(enable, reEnableTimeout, form);
    formTimers.add(enableTimerId);
}

function enable(form) {
    if (!form) {
        // Form no longer exists.
        return;
    }

    // Sanity: ensure we don't enable something twice.
    if (!form.hasAttribute(disabledAttributeName)) {
        return;
    }

    form.removeAttribute(disabledAttributeName);

    // Re-enable fieldsets.
    const fieldsets = form.querySelectorAll("fieldset");
    for (const fs of fieldsets) {
        fs.disabled = false;
    }

    // Re-enable buttons and remove the spinners.
    const submitButtons = form.querySelectorAll('button[type="submit"]');
    for (const btn of submitButtons) {
        btn.disabled = false;

        const spinners = btn.querySelectorAll(`span[${spinnerAttributeName}]`);
        for (const spinner of spinners) {
            spinner.remove();
        }
    }
}

/*
 * Cleans up any running timers or disabled forms
 */
function cleanUp() {
    for (const timerId of formTimers) {
        clearTimeout(timerId);
    }
    formTimers.clear();

    const forms = document.querySelectorAll(`form[${initAttributeName}]`);

    for (const form of forms) {
        enable(form);

        // Revert initialization
        form.removeEventListener("submit", handleFormSubmit);
        form.removeAttribute(initAttributeName);
    }
}

document.addEventListener("DOMContentLoaded", initDisableAfterSubmit);
document.addEventListener("htmx:load", initDisableAfterSubmit);

window.addEventListener("pageshow", e => {
    // Handle forward and backward navigations
    if (e.persisted) {
        cleanUp();
        initDisableAfterSubmit();
    }
});
