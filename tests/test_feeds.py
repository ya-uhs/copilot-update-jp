import unittest
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from scripts.generate_feed import select_articles, build_feed
from scripts.config import load_config


class FeedTests(unittest.TestCase):
    def test_ranked_feed_excludes_pending_old_and_other_family(self):
        base = dict(id='a', published_at='2026-09-25T00:00:00Z', translated=True, importance='high', family='github')
        articles = [base, {**base, 'id': 'pending', 'translated': False},
                    {**base, 'id': 'old', 'published_at': '2025-01-01T00:00:00Z'},
                    {**base, 'id': 'ms', 'family': 'microsoft365'},
                    {**base, 'id': 'low', 'importance': 'low'}]
        selected = select_articles(articles, dict(family='github', days=7, translated_only=True, sort='importance', limit=1), datetime(2026,9,26,tzinfo=timezone.utc))
        self.assertEqual([a['id'] for a in selected], ['a'])

    def test_fixed_guid_and_self_link(self):
        a = dict(id='fixed', source_url='https://example.com/a', title_original='English', published_at='2026-09-25T00:00:00Z')
        for translated in (False, True):
            doc = ET.fromstring(build_feed([{**a, 'translated': translated, 'title_ja': '日本語' if translated else ''}], 'https://example.com/'))
            self.assertEqual(doc.findtext('./channel/item/guid'), 'fixed')
            self.assertEqual(doc.find('./channel/{http://www.w3.org/2005/Atom}link').get('href'), 'https://example.com/feed.xml')

    def test_configuration_ids_are_unique(self):
        sources = load_config('sources')['sources']
        self.assertEqual(len(sources), len({s['id'] for s in sources}))
        feeds = load_config('feeds')['feeds']
        self.assertEqual(len(feeds), len({f['path'] for f in feeds}))
