"""Focused regression checks for shared content processing and configuration."""
import unittest
import tempfile
from pathlib import Path

from site_tools.navigation import navigation_pages
from site_tools.citations import Bibliography, link_citations, format_reference_text
from site_tools.config import load_json
from site_tools.validation import require


class CitationsTest(unittest.TestCase):
    def setUp(self):
        self.bibliography = Bibliography({
            'alpha-2026': {'text': 'Alpha source'},
            'beta-2025': {'text': 'Beta source'},
            'unused': {'text': 'Additional source'},
        })

    def test_first_appearance_and_reuse_across_pages(self):
        first = link_citations('<p>Evidence [@beta-2025] and <em>[@alpha-2026]</em>.</p>', self.bibliography, '../references/').html
        second = link_citations('<p>Repeated [@beta-2025].</p>', self.bibliography, './references/').html
        self.assertIn('aria-label="Citation 1">[1]</a>', first)
        self.assertIn('aria-label="Citation 2">[2]</a>', first)
        self.assertIn('href="./references/#ref-beta-2025" aria-label="Citation 1">[1]</a>', second)
        rendered = self.bibliography.render()
        self.assertLess(rendered.index('id="ref-beta-2025"'), rendered.index('id="ref-alpha-2026"'))
        self.assertIn('id="ref-unused" value="3"', rendered)
        self.assertEqual(rendered, self.bibliography.render())

    def test_preserves_attributes_links_code_and_entities(self):
        content = '<p title="[@unknown]">A &amp; B</p><!-- [@unknown] --><a href="#x">[@unknown]</a><code>[@unknown]</code><script>const x = "[@unknown]";</script>'
        self.assertEqual(link_citations(content, self.bibliography, '../references/').html, content)

    def test_unknown_key_fails(self):
        with self.assertRaisesRegex(ValueError, 'Unknown citation key: missing'):
            link_citations('<p>[@missing]</p>', self.bibliography, './references/')

    def test_preview_keys_come_from_prose_not_html_attributes_or_comments(self):
        linked = link_citations('<!-- data-citation="fake" --><p title="[@fake]">[@beta-2025] [@alpha-2026] [@beta-2025]</p>', self.bibliography, '../references/')
        self.assertEqual(linked.keys, ('beta-2025', 'alpha-2026'))

    def test_doi_punctuation_and_entities(self):
        result = format_reference_text('A & B (doi:10.1234/a&b).')
        self.assertIn('href="https://doi.org/10.1234/a&amp;b"', result)
        self.assertTrue(result.endswith('</a>).'))
        self.assertNotIn('&amp;amp;', result)

    def test_reference_order_keeps_original_numbers(self):
        bibliography = Bibliography(self.bibliography.references, numbering='reference-order')
        output = link_citations('<p>[@beta-2025] then [@alpha-2026] and [@beta-2025].</p>', bibliography, '../references/').html
        self.assertEqual(bibliography.numbers, {'beta-2025': 2, 'alpha-2026': 1})
        self.assertEqual(output.count('aria-label="Citation 2">[2]</a>'), 2)
        rendered = bibliography.render()
        self.assertLess(rendered.index('id="ref-alpha-2026"'), rendered.index('id="ref-beta-2025"'))

    def test_does_not_link_ordinary_brackets(self):
        content = '<p>[1] [note] [1, 2]</p>'
        self.assertEqual(link_citations(content, self.bibliography, './references/').html, content)

    def test_reference_text_is_escaped_and_source_links_are_clickable(self):
        bibliography = Bibliography({'example': {'text': 'A & B. doi:10.1234/example', 'url': 'https://example.com/?a=1&b=2'}})
        rendered = bibliography.render()
        self.assertIn('A &amp; B.', rendered)
        self.assertIn('href="https://doi.org/10.1234/example"', rendered)
        self.assertIn('href="https://example.com/?a=1&amp;b=2"', rendered)
        with self.assertRaises(ValueError):
            Bibliography({'unsafe': {'text': 'Source', 'url': 'javascript:alert(1)'}})


class NavigationTest(unittest.TestCase):
    def test_rejects_unsafe_or_duplicate_routes(self):
        for slug in ['../escape', '/absolute', 'UPPER', 'two--hyphens', 'home', 'src', 'assets', 'scripts']:
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                navigation_pages([{'title': 'Home', 'slug': ''}, {'title': 'Page', 'slug': slug}])
        with self.assertRaises(ValueError):
            navigation_pages([{'title': 'Home', 'slug': ''}, {'title': 'Duplicate', 'slug': ''}])


class BuildTest(unittest.TestCase):
    def test_duplicate_json_keys_fail_with_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'references.json'
            path.write_text('{"source": 1, "source": 2}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'references.json.*Duplicate JSON key: source'):
                load_json(path)

    def test_validator_failure_is_explicit(self):
        with self.assertRaisesRegex(ValueError, 'broken link'):
            require(False, 'broken link')


if __name__ == '__main__':
    unittest.main()
