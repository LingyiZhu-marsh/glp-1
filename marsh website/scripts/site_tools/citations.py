"""Resolve stable citation keys and render a numbered bibliography."""
from html import escape
from html.parser import HTMLParser
from dataclasses import dataclass
import re
from urllib.parse import urlsplit

KEY = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def format_reference_text(text):
    """Link DOI tokens before HTML escaping, leaving sentence punctuation outside."""
    parts = []
    position = 0
    for match in re.finditer(r'doi:(10\.[0-9]+/[^\s<>]+)', text):
        doi = match[1].rstrip('.,;')
        while doi.endswith(')') and doi.count(')') > doi.count('('):
            doi = doi[:-1]
        parts.append(escape(text[position:match.start()]))
        parts.append(f'doi:<a href="https://doi.org/{escape(doi, quote=True)}">{escape(doi)}</a>')
        parts.append(escape(match[1][len(doi):]))
        position = match.end()
    parts.append(escape(text[position:]))
    return ''.join(parts)


@dataclass(frozen=True)
class LinkedContent:
    html: str
    keys: tuple[str, ...]


class Bibliography:
    def __init__(self, references, numbering='first-appearance'):
        if numbering not in ('first-appearance', 'reference-order'):
            raise ValueError(f'Unknown citation numbering mode: {numbering}')
        self.numbering = numbering
        if not isinstance(references, dict):
            raise ValueError('References must be an object keyed by citation identifier.')
        for key, entry in references.items():
            if not isinstance(key, str) or not KEY.fullmatch(key) or not isinstance(entry, dict) or not isinstance(entry.get('text'), str) or not entry['text'].strip():
                raise ValueError(f'Invalid reference: {key!r}')
            if 'url' in entry:
                if not isinstance(entry['url'], str):
                    raise ValueError(f'Invalid source URL for {key}')
                url = urlsplit(entry['url'])
                if url.scheme not in ('http', 'https') or not url.netloc:
                    raise ValueError(f'Invalid source URL for {key}')
        self.references = references
        self.reference_numbers = {key: number for number, key in enumerate(references, start=1)}
        self.numbers = {}

    def cite(self, key, destination):
        if key not in self.references:
            raise ValueError(f'Unknown citation key: {key}')
        if key not in self.numbers:
            self.numbers[key] = self.reference_numbers[key] if self.numbering == 'reference-order' else len(self.numbers) + 1
        number = self.numbers[key]
        href = escape(f'{destination}#ref-{key}', quote=True)
        return f'<a class="citation" data-citation="{key}" href="{href}" aria-label="Citation {number}">[{number}]</a>'

    def reference_html(self, key):
        """Share identical reference formatting between the list and overlay."""
        entry = self.references[key]
        text = format_reference_text(entry['text'])
        if 'url' in entry:
            url = escape(entry['url'], quote=True)
            text += f' Available from: <a href="{url}">{url}</a>'
        return text

    def render(self):
        # Keep supplied but not-yet-cited sources visible after cited sources.
        order = list(self.references) if self.numbering == 'reference-order' else list(self.numbers) + [key for key in self.references if key not in self.numbers]
        parts = ['<ol class="references">']
        for number, key in enumerate(order, start=1):
            text = self.reference_html(key)
            parts.append(f'  <li id="ref-{key}" value="{number}">{text}</li>')
        parts.append('</ol>')
        return '\n'.join(parts)


class CitationLinker(HTMLParser):
    PROTECTED = {'a', 'code', 'pre', 'script', 'style', 'textarea'}

    def __init__(self, bibliography, destination):
        super().__init__(convert_charrefs=False)
        self.destination = destination
        self.bibliography = bibliography
        self.parts = []
        self.protected = []
        self.keys = {}

    def handle_starttag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())
        if tag in self.PROTECTED:
            self.protected.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')
        if self.protected and self.protected[-1] == tag:
            self.protected.pop()

    def handle_data(self, text):
        if not self.protected:
            text = re.sub(r'\[@([^\]\s]+)\]', self.link, text)
        self.parts.append(text)

    def link(self, match):
        key = match.group(1)
        html = self.bibliography.cite(key, self.destination)
        self.keys[key] = None
        return html

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_comment(self, text):
        self.parts.append(f'<!--{text}-->')

    def handle_decl(self, text):
        self.parts.append(f'<!{text}>')


def link_citations(content, bibliography, destination):
    parser = CitationLinker(bibliography, destination)
    parser.feed(content)
    parser.close()
    return LinkedContent(''.join(parser.parts), tuple(parser.keys))
