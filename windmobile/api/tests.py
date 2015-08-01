# coding=utf-8

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from windmobile.api import diacritics


class SimpleTest(TestCase):
    def test_diacritics(self):
        """
        Test diacritics functions
        """
        self.assertEqual(diacritics.normalize('Élèves!'), 'Eleves!')
        self.assertEqual(diacritics.create_regexp('Eleves!'), '[ÈÉÊËE]l[èéêëe]v[èéêëe][šßs]!')

