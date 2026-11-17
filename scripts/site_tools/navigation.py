"""Navigation validation, page URLs, and shared navigation rendering."""
from html import escape
import re

RESERVED_SLUGS = {'home', 'assets', 'src', 'scripts', '404'}


def page_url(page, base):
    """Resolve a page against the site's base directory."""
    return base + (page['slug'] + '/' if page['slug'] else '')


def page_link(page, base, current):
    """Create a repository-relative link and mark the current page."""
    href = page_url(page, base)
    active = ' aria-current="page"' if page['slug'] == current else ''
    home_class = ' class="nav-home-link"' if not page['slug'] else ''
    return f'<a{home_class} href="{escape(href)}"{active}>{escape(page["title"])}</a>'


def render_navigation(items, base, current, template):
    """Render the shared navigation for root and single-level page URLs."""
    home = next(item for item in items if item.get('slug') == '')
    parts = []
    for index, item in enumerate(items):
        if 'children' not in item:
            parts.append('    ' + page_link(item, base, current))
            continue
        menu_id = f'nav-menu-{index}'
        active = any(page['slug'] == current for page in item['children'])
        group_class = 'dropdown is-current' if active else 'dropdown'
        parts.extend([
            f'    <div class="{group_class}">',
            f'      <button type="button" class="dropdown-toggle" aria-expanded="true" aria-controls="{menu_id}"><span class="nav-label">{escape(item["title"])}</span> <span class="nav-chevron" aria-hidden="true">▾</span></button>',
            f'      <div class="dropdown-menu" id="{menu_id}">',
        ])
        parts.extend('        ' + page_link(page, base, current) for page in item['children'])
        parts.extend(['      </div>', '    </div>'])
    return template.substitute(home_link=page_link(home, base, current), items='\n'.join(parts))


def render_page_navigation(pages, index, base):
    """Use the main menu's reading order for previous and next links."""
    parts = ['  <nav class="page-navigation" aria-label="Page navigation">']
    for offset, direction, label in [(-1, 'prev', '← Previous'), (1, 'next', 'Next →')]:
        target = index + offset
        if not 0 <= target < len(pages):
            continue
        page = pages[target]
        parts.append(
            f'    <a class="page-navigation-{direction}" rel="{direction}" href="{escape(page_url(page, base))}">'
            f'<span class="page-navigation-label">{label}</span> '
            f'<span>{escape(page["title"])}</span></a>'
        )
    parts.append('  </nav>')
    return '\n'.join(parts)


def navigation_pages(items):
    """Validate the navigation contract before it becomes paths or links."""
    if not isinstance(items, list) or not items:
        raise ValueError('Navigation must be a nonempty list.')
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('title'), str) or not item['title'].strip():
            raise ValueError('Every navigation entry needs a title.')
        if 'children' in item:
            if 'slug' in item or not isinstance(item['children'], list) or not item['children']:
                raise ValueError('Navigation groups need children and no slug.')
            for child in item['children']:
                if not isinstance(child, dict) or not isinstance(child.get('title'), str) or not child['title'].strip() or 'children' in child:
                    raise ValueError('Dropdown children must be titled pages, not nested groups.')
    pages = [page for item in items for page in item.get('children', [item])]
    slugs = [page.get('slug') for page in pages]
    for slug in slugs:
        if not isinstance(slug, str) or (slug and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug)):
            raise ValueError(f'Invalid page slug: {slug!r}')
        if slug in RESERVED_SLUGS:
            raise ValueError(f'Reserved page slug: {slug}')
    if len(slugs) != len(set(slugs)):
        raise ValueError('Page slugs must be unique.')
    if not any(item.get('slug') == '' for item in items):
        raise ValueError('Navigation needs a top-level Home page with an empty slug.')
    return pages

