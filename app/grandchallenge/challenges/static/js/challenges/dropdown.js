
function handle_nav_tab_dropdown() {
    if (window.innerWidth < 576) {
        // 576 px is the bootstrap breakpoint for sm
        navs_to_dropdown(false, true);
    } else if (window.innerWidth < 992) {
        // 992 px is the bootstrap breakpoint for lg
        navs_to_dropdown();
    } else {
        navs_to_dropdown(true);
        }
}

function navs_to_dropdown(reverse = false, horiz_page_pills = false) {
    // Get all elements that need to change class
    const containers = document.querySelectorAll('.nav-tab-dropdown-container,.nav-pill-dropdown-container');
    const page_containers = document.getElementsByClassName("nav-pill-pages-container");

    const ulDropdownClasses = ["dropdown-menu", "dropdown-menu-left"];
    const ulTabClasses = ["nav", "nav-tabs", "border-0"];
    const itemDropdownClasses = ["dropdown-item", "challengeDropdown"];
    const itemTabPillClasses = ["nav-item"];
    const ulPillClasses = ["nav", "nav-pills", "col-12", "mb-3"];
    const ulHorizPagePillClasses = ["d-flex", "align-items-stretch", "mb-3"];
    const ulVertPagePillClasses = ["flex-column"];

    for (let page_container of page_containers) {
        let ul_pages  = page_container.querySelector("ul");

        if (horiz_page_pills === true) {
            ul_pages.classList.remove(...ulVertPagePillClasses);
            ul_pages.classList.add(...ulHorizPagePillClasses);
        } else {
            ul_pages.classList.add(...ulVertPagePillClasses);
            ul_pages.classList.remove(...ulHorizPagePillClasses);
        }
    }

    // Change the classes
    for (let container of containers) {
        let ul  = container.querySelector("ul");

        if (reverse === true) {
            container.classList.remove("dropdown");
            ul.classList.remove(...ulDropdownClasses);

            if (container.classList.contains("nav-tab-dropdown-container")) {
                ul.classList.add(...ulTabClasses);
            } else if (container.classList.contains("nav-pill-dropdown-container")) {
                ul.classList.add(...ulPillClasses);
            }
        }
        else {
            container.classList.add("dropdown");
            ul.classList.add(...ulDropdownClasses);

            if (container.classList.contains("nav-tab-dropdown-container")) {
                ul.classList.remove(...ulTabClasses);
            } else if (container.classList.contains("nav-pill-dropdown-container")) {
                ul.classList.remove(...ulPillClasses);
            }
        }

        let items = container.querySelectorAll("li");

        for (let item of items) {
            if (reverse === true) {
                item.classList.add(...itemTabPillClasses);
                item.classList.remove(...itemDropdownClasses);
            } else {
                item.classList.add(...itemDropdownClasses);
                item.classList.remove(...itemTabPillClasses);
            }
        }
    }

}

window.addEventListener('resize', handle_nav_tab_dropdown);

handle_nav_tab_dropdown();
