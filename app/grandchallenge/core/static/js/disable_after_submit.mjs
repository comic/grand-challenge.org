/**
 * @description
 * This module provides functionality to temporarily disable all fieldsets (and indirectly their children)
 * and show a spinner on submit buttons within forms, when the forms have the
 * `gc-disable-fieldsets-after-submit` attribute. This prevents duplicate submissions.
 *
 * Fieldsets are re-enabled and spinners removed after a short timeout.
 */

// Timeout in milliseconds before re-enabling fieldsets and removing spinners.
const reEnableTimeout = 10000;

// Attribute names
const baseAttributeName = "gc-disable-after-submit";
const initAttributeName = `${baseAttributeName}-initialized`;
const activeAttributeName = `${baseAttributeName}-disabled`;
const spinnerAttributeName = `${baseAttributeName}-spinner`;

function disableFieldSets(form) {
    if (!form) {
        // Form no longer exists.
        return;
    }

    // Sanity: ensure we don't disable something twice.
    if (form.hasAttribute(activeAttributeName)) {
        return;
    }

    form.setAttribute(activeAttributeName, "true");

    // Disable fieldsets.
    const fieldsets = form.querySelectorAll("fieldset");
    for (const fs of fieldsets) {
        fs.disabled = true;
    }

    // Add a spinner
    const submitButtons = form.querySelectorAll('button[type="submit"]');
    for (const btn of submitButtons) {
        const spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm mr-1";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        spinner.setAttribute(spinnerAttributeName, "true");
        btn.prepend(spinner);
    }

    // Re-enable after a while to safeguard against unforeseen errors / cancelations.
    setTimeout(enableFieldSets, reEnableTimeout, form);
}

function enableFieldSets(form) {
    if (!form) {
        // Form no longer exists.
        return;
    }

    // Sanity: ensure we don't enable something twice.
    if (!form.hasAttribute(activeAttributeName)) {
        return;
    }

    form.removeAttribute(activeAttributeName);

    // Re-enable fieldsets.
    const fieldsets = form.querySelectorAll("fieldset");
    for (const fs of fieldsets) {
        fs.disabled = false;
    }

    // Remove the spinners.
    const spinners = form.querySelectorAll(`span[${spinnerAttributeName}]`);
    for (const spinner of spinners) {
        spinner.remove();
    }
}

function handleFormSubmit(event) {
    const form = event.currentTarget;

    if (form.hasAttribute(activeAttributeName)) {
        event.preventDefault();
        return;
    }

    // Delay the disable so form data is actually submitted.
    // Disabled-element values are thus not excluded.
    setTimeout(disableFieldSets, 0, form);
}

function initDisableAfterSubmit(elem) {
    const forms = elem.querySelectorAll(
        "form[gc-disable-fieldsets-after-submit]",
    );

    for (const form of forms) {
        if (!form.hasAttribute(initAttributeName)) {
            form.addEventListener("submit", handleFormSubmit);
            form.setAttribute(initAttributeName, "true");
        }
    }
}

// Initialize when DOM is ready.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () =>
        initDisableAfterSubmit(document),
    );
} else {
    initDisableAfterSubmit(document);
}

// Handle inserted forms via HTMX.
if (typeof htmx !== "undefined" && htmx.onLoad) {
    htmx.onLoad(elem => initDisableAfterSubmit(elem));
}
