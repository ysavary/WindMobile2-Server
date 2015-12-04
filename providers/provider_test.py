import unittest

from provider import Provider


class ProviderTest(unittest.TestCase):
    def test_compute_elevation(self):
        provider = Provider("mongodb://localhost:27017/windmobile", "AIzaSyAK2QNa8fWYCDK1o3McUP4--qdNtzl-wsQ")

        # Le Suchet
        elevation, is_peak = provider.compute_elevation(46.7724, 6.4662)
        self.assertTrue(is_peak)

        # Mont Poupet
        elevation, is_peak = provider.compute_elevation(46.9722, 5.86472)
        self.assertFalse(is_peak)
