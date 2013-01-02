# coding=utf-8

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
import diacritics

class SimpleTest(TestCase):
    def test_diacritics(self):
        """
        Test diacritics functions
        """
        self.assertEqual(diacritics.normalize(u'Élèves!'), u'Eleves!')
        self.assertEqual(diacritics.create_regexp(u'Eleves!'), u'[ÈÉÊËE]l[èéêëe]v[èéêëe][šßs]!')

