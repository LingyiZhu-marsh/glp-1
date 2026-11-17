"""Validate generated pages without third-party dependencies. Run after build.py."""
from html.parser import HTMLParser
import re
from urllib.parse import unquote, urljoin, urlsplit

from .project import ROOT, site_base_path
from .navigation import navigation_pages
from .config import load_json
from .outputs import validate_outputs


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = []
        self.controls = []
        self.links = []
        self.sequence = {}
        self.headings = 0
        self.citations = []
        self.home_url = None
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'return-home' in attrs.get('class', '').split():
            self.home_url = attrs.get('href')
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'aria-controls' in attrs:
            self.controls.append(attrs['aria-controls'])
        self.controls.extend(attrs.get('aria-labelledby', '').split())
        if 'data-citation' in attrs:
            self.citations.append(attrs['data-citation'])
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append(attrs[key])
        if tag == 'a' and attrs.get('rel') in ('prev', 'next'):
            self.sequence[attrs['rel']] = attrs['href']
        self.headings += tag == 'h1'


def require(condition, message):
    """Validation must run even when Python is invoked with -O."""
    if not condition:
        raise ValueError(message)


def validate(root=ROOT):
    root = root.resolve()
    pages = navigation_pages(load_json(root / 'src' / 'navigation.json'))
    output_root = root / 'build'
    expected_outputs = {f'{page["slug"]}/index.html' if page['slug'] else 'index.html' for page in pages} | {'404.html'}
    validate_outputs(output_root, expected_outputs)
    parsed_pages = {}

    def parse(path):
        if path not in parsed_pages:
            parsed_pages[path] = Page(path)
        return parsed_pages[path]

    def check_links(parsed, output, current, prefix):
        for href in parsed.links:
            if href.startswith('#'):
                require(unquote(href[1:]) in parsed.ids, f'{output}: missing fragment: {href}')
                continue
            url = urlsplit(urljoin(current, href))
            if url.netloc != 'example.test':
                continue
            require(url.path.startswith(prefix), f'{output}: link escapes site base: {href}')
            target = (output_root / unquote(url.path[len(prefix):])).resolve()
            require(target.is_relative_to(output_root), f'{output}: link escapes build: {href}')
            if target.is_dir():
                target /= 'index.html'
            require(target.is_file(), f'{output}: missing link or asset: {href}')
            if url.fragment:
                require(unquote(url.fragment) in parse(target).ids, f'{output}: missing fragment: {href}')

    for index, page in enumerate(pages):
        slug = page['slug']
        output = output_root / slug / 'index.html'
        parsed = parse(output)
        require(parsed.headings == 1, f'{output}: expected one main heading')
        require(len(parsed.ids) == len(set(parsed.ids)), f'{output}: duplicate IDs')
        require(all(control in parsed.ids for control in parsed.controls), f'{output}: missing accessible label or control target')
        require(all(f'citation-content-{key}' in parsed.ids for key in parsed.citations), f'{output}: missing citation preview')
        expected = {}
        for offset, direction in [(-1, 'prev'), (1, 'next')]:
            if 0 <= index + offset < len(pages):
                expected[direction] = pages[index + offset]['slug']
        require(parsed.sequence.keys() == expected.keys(), f'{output}: incorrect pager endpoints')
        for prefix in ('/', '/repository/'):
            current = 'https://example.test' + prefix + (slug + '/' if slug else '')
            check_links(parsed, output, current, prefix)
            for direction, target_slug in expected.items():
                target_url = 'https://example.test' + prefix + (target_slug + '/' if target_slug else '')
                require(urljoin(current, parsed.sequence[direction]) == target_url, f'{output}: incorrect reading order')
    error_path = output_root / '404.html'
    error_page = parse(error_path)
    base = site_base_path(load_json(root / 'src/site.json'))
    require(error_page.headings == 1, '404.html: expected one main heading')
    require(error_page.home_url == base, '404.html: Home link must target the site root')
    require(not error_page.sequence, '404.html: error pages must not enter the reading sequence')
    for requested in ('missing-page', 'nested/missing/page/'):
        check_links(error_page, error_path, 'https://example.test' + base + requested, base)
    for stylesheet in (output_root / 'assets').glob('*.css'):
        for url in re.findall(r'url\([\'\"]?([^\)\'\"]+)', stylesheet.read_text(encoding='utf-8')):
            if urlsplit(url).scheme or url.startswith('#'):
                continue
            require((stylesheet.parent / unquote(urlsplit(url).path)).is_file(), f'{stylesheet}: missing CSS asset: {url}')
    print(f'Validated {len(pages)} report pages and the 404 page: headings, IDs, controls, links, assets, and reading order.')

