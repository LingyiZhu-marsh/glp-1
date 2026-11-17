"""Compose source content and shared templates before writing static pages."""
from dataclasses import replace
from html import escape
from pathlib import Path
from string import Template
import shutil
from tempfile import mkdtemp

from .citations import Bibliography, link_citations
from .config import load_json
from .navigation import navigation_pages, render_navigation, render_page_navigation
from .project import ROOT, site_base_path
from .outputs import publish_directory, remove_temporary, write_manifest


def load_content(source, pages, site, bibliography):
    """Resolve citations in reading order, then insert the reference list."""
    contents = {}
    for page in pages:
        slug = page['slug']
        base = '../' if slug else './'
        raw = (source / 'pages' / f'{slug or "home"}.html').read_text(encoding='utf-8')
        try:
            contents[slug] = link_citations(raw, bibliography, base + site['citations_slug'] + '/')
        except ValueError as error:
            raise ValueError(f'{slug or "home"}: {error}') from error
    marker = '<!-- REFERENCES -->'
    references = contents[site['citations_slug']]
    if references.html.count(marker) != 1:
        raise ValueError('The citations page must contain exactly one <!-- REFERENCES --> marker.')
    contents[site['citations_slug']] = replace(references, html=references.html.replace(marker, bibliography.render()))
    return contents


def render_pages(root):
    """Prepare all output in memory; source errors never overwrite existing pages."""
    source = root / 'src'
    items = load_json(source / 'navigation.json')
    site = load_json(source / 'site.json')
    if not isinstance(site, dict):
        raise ValueError('site.json must contain an object.')
    for field in ('title', 'short_title', 'description', 'citations_slug'):
        if not isinstance(site.get(field), str) or not site[field].strip():
            raise ValueError(f'site.json needs a nonempty {field}.')
    pages = navigation_pages(items)
    if site['citations_slug'] not in {page['slug'] for page in pages}:
        raise ValueError('The configured citations page is missing from navigation.')
    template = Template((source / 'templates/page.html').read_text(encoding='utf-8'))
    navigation_template = Template((source / 'templates/navigation.html').read_text(encoding='utf-8'))
    bibliography = Bibliography(
        load_json(source / 'references.json'),
        numbering=site.get('citation_numbering', 'first-appearance'),
    )
    contents = load_content(source, pages, site, bibliography)
    outputs = {}
    for index, page in enumerate(pages):
        slug = page['slug']
        base = '../' if slug else './'
        content = contents[slug]
        citation_templates = '\n'.join(
            f'<template id="citation-content-{key}">{bibliography.reference_html(key)}</template>'
            for key in content.keys
        )
        title = f'{page["title"]} | {site["short_title"]}' if slug else site['title']
        outputs[f'{slug}/index.html' if slug else 'index.html'] = template.substitute(
            title=escape(title), description=escape(site['description']), base=base,
            navigation=render_navigation(items, base, slug, navigation_template), content=content.html,
            page_navigation=render_page_navigation(pages, index, base),
            page_class='report-page' if slug else 'home-page',
            citation_templates=citation_templates,
            robots='',
        )
    # Error pages are served at the requested URL, not necessarily /404.html.
    base = site_base_path(site)
    error_content = Template((source / 'pages/404.html').read_text(encoding='utf-8')).substitute(home_url=escape(base))
    outputs['404.html'] = template.substitute(
        title=escape(f'Page not found | {site["short_title"]}'),
        description='The requested page could not be found.', base=base,
        navigation='', content=error_content, page_navigation='',
        page_class='not-found-page', citation_templates='',
        robots='<meta name="robots" content="noindex">',
    )
    return outputs


def build(root=ROOT):
    root = root.resolve()
    outputs = render_pages(root)
    staging = Path(mkdtemp(prefix='.build-', dir=root))
    try:
        shutil.copytree(root / 'src/assets', staging / 'assets')
        for name, html in outputs.items():
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(html, encoding='utf-8')
        (staging / '.nojekyll').touch()
        write_manifest(staging, outputs)
        publish_directory(root, staging)
    finally:
        remove_temporary(staging, root)
    print(f'Built {len(outputs)} pages in build/.')
