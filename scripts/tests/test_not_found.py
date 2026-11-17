"""Check error-page links when the browser remains on a missing URL."""
import os
import re
import unittest
from unittest.mock import patch
from urllib.parse import urljoin

from site_tools.builder import render_pages
from site_tools.project import ROOT, site_base_path


class NotFoundTest(unittest.TestCase):
    def test_error_links_work_at_nested_missing_urls(self):
        for configured in ('', '/', '/project-report'):
            with self.subTest(base=configured), patch.dict(os.environ, {'SITE_BASE_PATH': configured}):
                pages = render_pages(ROOT)
                html = pages['404.html']
                base = configured.rstrip('/') + '/' if configured else '/'
                self.assertIn(f'class="return-home" href="{base}"', html)
                for requested in ('missing', 'nested/missing/page/'):
                    current = 'https://example.test' + base + requested
                    for href in re.findall(r'(?:href|src)="([^"]+)"', html):
                        if href.startswith('#'):
                            continue
                        target = urljoin(current, href)
                        self.assertTrue(target.startswith('https://example.test' + base))
                        self.assertTrue(href == base or href.startswith(base + 'assets/'))

    def test_error_page_is_not_part_of_the_report_sequence(self):
        html = render_pages(ROOT)['404.html']
        self.assertIn('<h1>Page not found</h1>', html)
        self.assertIn('name="robots" content="noindex"', html)
        self.assertNotIn('class="page-navigation"', html)
        self.assertNotIn('class="top-nav"', html)

    def test_invalid_base_path_is_rejected(self):
        for value in ('https://example.test/report', '//example.test/report', '../report', '/report/../', '/report?query=1'):
            with self.subTest(value=value), patch.dict(os.environ, {'SITE_BASE_PATH': value}):
                with self.assertRaises(ValueError):
                    site_base_path({})
