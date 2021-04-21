
function handleNavTabDropdown() {
  if (window.innerWidth < 576) {
    // 576 px is the bootstrap breakpoint for sm
    navsToDropdown(false, true);
  } else if (window.innerWidth < 992) {
    // 992 px is the bootstrap breakpoint for lg
    navsToDropdown();
  } else {
    navsToDropdown(true);
  }
}

function navsToDropdown(reverse = false, horizPagePills = false) {
  // Get all elements that need to change class
  const containers = document.querySelectorAll('.nav-tab-dropdown-container,.nav-pill-dropdown-container');
  const pageContainers = document.getElementsByClassName("nav-pill-pages-container");

  const ulDropdownClasses = ["dropdown-menu", "dropdown-menu-left"];
  const ulTabClasses = ["nav", "nav-tabs", "border-0"];
  const itemDropdownClasses = ["dropdown-item", "challengeDropdown"];
  const itemTabPillClasses = ["nav-item"];
  const ulPillClasses = ["nav", "nav-pills", "col-12", "mb-3"];
  const ulHorizPagePillClasses = ["d-flex", "align-items-stretch", "mb-3"];
  const ulVertPagePillClasses = ["flex-column"];

  for (const pageContainer of pageContainers) {
    const ulPages  = pageContainer.querySelector("ul");

    if (horizPagePills === true) {
      ulPages.classList.remove(...ulVertPagePillClasses);
      ulPages.classList.add(...ulHorizPagePillClasses);
    } else {
      ulPages.classList.add(...ulVertPagePillClasses);
      ulPages.classList.remove(...ulHorizPagePillClasses);
    }
  }

  // Change the classes
  for (const container of containers) {
    const ul  = container.querySelector("ul");

    if (reverse === true) {
      container.classList.remove("dropdown");
      ul.classList.remove(...ulDropdownClasses);

      if (container.classList.contains("nav-tab-dropdown-container")) {
        ul.classList.add(...ulTabClasses);
      } else if (container.classList.contains("nav-pill-dropdown-container")) {
        ul.classList.add(...ulPillClasses);
      }
    } else {
      container.classList.add("dropdown");
      ul.classList.add(...ulDropdownClasses);

      if (container.classList.contains("nav-tab-dropdown-container")) {
        ul.classList.remove(...ulTabClasses);
      } else if (container.classList.contains("nav-pill-dropdown-container")) {
        ul.classList.remove(...ulPillClasses);
      }
    }

    const items = container.querySelectorAll("li");

    for (const item of items) {
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

window.addEventListener('resize', handleNavTabDropdown);

handleNavTabDropdown();
