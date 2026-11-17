// Direct file previews need explicit filenames; served sites keep clean URLs.
function prepareFileLinks() {
  if (window.location.protocol !== 'file:') return;
  for (const link of document.querySelectorAll('a[href]')) {
    const href = link.getAttribute('href');
    if (href.startsWith('#')) continue;
    const destination = new URL(href, window.location.href);
    if (destination.protocol === 'file:' && destination.pathname.endsWith('/')) {
      destination.pathname += 'index.html';
      link.href = destination.href;
    }
  }
}

// Both menu types use one source of truth for their expanded state.
function createDisclosure(button, panel, { manageVisibility = true, onChange = () => {} } = {}) {
  return {
    button,
    panel,
    get isOpen() { return button.getAttribute('aria-expanded') === 'true'; },
    setOpen(open) {
      button.setAttribute('aria-expanded', String(open));
      if (manageVisibility) panel.hidden = !open;
      onChange(open);
    },
  };
}

function initializeNavigation(navigation) {
  if (!navigation) return;
  const menuToggle = navigation.querySelector('.mobile-menu-toggle');
  const links = navigation.querySelector('.nav-links');
  if (!menuToggle || !links) return;

  // Keep this breakpoint aligned with the navigation media query in styles.css.
  const mobileViewport = window.matchMedia('(max-width: 1000px)');
  const groups = [...navigation.querySelectorAll('.dropdown')].map(element => {
    const group = createDisclosure(element.querySelector('button'), element.querySelector('.dropdown-menu'));
    group.setOpen(false);
    group.element = element;
    return group;
  });
  const mobileMenu = createDisclosure(menuToggle, links, {
    manageVisibility: false, // CSS keeps the same panel visible on desktop.
    onChange: open => navigation.classList.toggle('is-open', open),
  });

  function closeGroups(except = null) {
    groups.forEach(group => { if (group !== except) group.setOpen(false); });
  }

  function closeMobileMenu(returnFocus = false) {
    mobileMenu.setOpen(false);
    closeGroups();
    if (returnFocus) menuToggle.focus();
  }

  for (const group of groups) {
    group.button.addEventListener('click', () => {
      const opening = !group.isOpen;
      closeGroups();
      group.setOpen(opening);
    });
    group.element.addEventListener('keydown', event => {
      if (event.key === 'Escape' && group.isOpen) {
        event.stopPropagation();
        group.setOpen(false);
        group.button.focus();
      }
      if (event.key === 'ArrowDown' && event.target === group.button) {
        event.preventDefault();
        closeGroups(group);
        group.setOpen(true);
        group.panel.querySelector('a')?.focus();
      }
    });
    group.element.addEventListener('focusout', event => {
      if (!group.element.contains(event.relatedTarget)) group.setOpen(false);
    });
  }

  menuToggle.addEventListener('click', () => {
    const opening = !mobileMenu.isOpen;
    closeGroups();
    mobileMenu.setOpen(opening);
  });
  navigation.addEventListener('click', event => {
    if (!event.target.closest('a')) return;
    if (mobileViewport.matches) closeMobileMenu(true);
    else closeGroups();
  });
  navigation.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobileViewport.matches && mobileMenu.isOpen) {
      closeMobileMenu(true);
    }
  });
  navigation.addEventListener('focusout', event => {
    if (!navigation.contains(event.relatedTarget)) closeMobileMenu();
  });
  document.addEventListener('click', event => {
    const group = groups.find(group => group.element.contains(event.target));
    closeGroups(group);
    if (!navigation.contains(event.target)) closeMobileMenu();
  });
  mobileViewport.addEventListener('change', () => {
    const focused = document.activeElement;
    const focusWasInLinks = links.contains(focused);
    const focusedGroup = groups.find(group => group.panel.contains(focused));
    closeMobileMenu();
    if (mobileViewport.matches && focusWasInLinks) menuToggle.focus();
    else if (!mobileViewport.matches && focusedGroup) focusedGroup.button.focus();
    else if (!mobileViewport.matches && focused === menuToggle) {
      links.querySelector('a')?.focus();
    }
  });
  navigation.classList.add('is-enhanced');
}

prepareFileLinks();
initializeNavigation(document.querySelector('.top-nav'));
