import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psfr
from PIL import Image


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.post = psfr.validate_post(psfr.read_json(psfr.ROOT / 'demo.json'))
        self.channel = {'id': 'test-channel', 'service': 'tiktok'}

    def test_real_graphic_is_valid_and_fits_tiktok_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'graphic.jpg'
            psfr.render(self.post, target)
            with Image.open(target) as image:
                self.assertEqual(image.size, (1080, 1920))
                self.assertEqual(image.format, 'JPEG')
                image.verify()
            self.assertLess(target.stat().st_size, 8_000_000)

    def test_mutation_timeout_blocks_blind_retry(self):
        receipt, saved = {}, []
        def save():
            saved.append(receipt.copy())
        with patch.object(psfr, 'buffer', side_effect=TimeoutError) as call:
            with self.assertRaises(RuntimeError):
                psfr.deliver(self.channel, self.post, 'https://example.com/a.jpg', 'draft', receipt, save)
            self.assertEqual(saved[0]['status'], 'pending')
            self.assertEqual(receipt['status'], 'uncertain')
            with self.assertRaises(RuntimeError):
                psfr.deliver(self.channel, self.post, 'https://example.com/a.jpg', 'draft', receipt, save)
            self.assertEqual(call.call_count, 1)

    def test_success_is_not_posted_twice(self):
        receipt = {}
        with patch.object(psfr, 'buffer', return_value={'createPost': {'post': {'id': 'receipt123'}}}) as call:
            for _ in range(2):
                psfr.deliver(self.channel, self.post, 'https://example.com/a.jpg', 'draft', receipt, lambda: None)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(receipt['post_id'], 'receipt123')

    def test_draft_does_not_queue_for_publication(self):
        for mode in ('draft', 'test-draft'):
            query = psfr.create_query(self.channel, self.post, 'https://example.com/a.jpg', mode)
            self.assertIn('saveToDraft: true', query)
            self.assertIn('tiktok:', query)

    def test_bad_content_stops_before_graphic_or_publishing(self):
        with self.assertRaises(ValueError):
            psfr.validate_post({**self.post, 'headline': 'x' * 86})

    def test_reservation_must_be_saved_before_external_call(self):
        with patch.object(psfr, 'buffer') as call:
            def failed_save():
                raise RuntimeError('Unable to save reservation')
            with self.assertRaises(RuntimeError):
                psfr.deliver(self.channel, self.post, 'https://example.com/a.jpg', 'queue', {}, failed_save)
            call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
