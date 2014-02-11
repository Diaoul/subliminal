#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from unittest import TestCase, TestSuite, TestLoader, TextTestRunner
from babelfish import Language
from subliminal import provider_manager
from subliminal.tests.common import MOVIES, EPISODES


class ProviderTestCase(TestCase):
    provider_name = ''

    def setUp(self):
        self.Provider = provider_manager[self.provider_name]


class Addic7edProviderTestCase(ProviderTestCase):
    provider_name = 'addic7ed'

    def test_find_show_id(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('the big bang')
        self.assertEqual(show_id, 126)

    def test_find_show_id_no_year(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('dallas')
        self.assertEqual(show_id, 802)

    def test_find_show_id_year(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('dallas', 2012)
        self.assertEqual(show_id, 2559)

    def test_find_show_id_error(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('the big how i met your mother')
        self.assertIsNone(show_id)

    def test_get_show_ids(self):
        with self.Provider() as provider:
            show_ids = provider.get_show_ids()
        self.assertIn('the big bang theory', show_ids)
        self.assertEqual(show_ids['the big bang theory'], 126)

    def test_get_show_ids_no_year(self):
        with self.Provider() as provider:
            show_ids = provider.get_show_ids()
        self.assertIn('dallas', show_ids)
        self.assertEqual(show_ids['dallas'], 802)

    def test_get_show_ids_year(self):
        with self.Provider() as provider:
            show_ids = provider.get_show_ids()
        self.assertIn('dallas (2012)', show_ids)
        self.assertEqual(show_ids['dallas (2012)'], 2559)

    def test_query_episode_0(self):
        video = EPISODES[0]
        languages = {Language('tur'), Language('rus'), Language('heb'), Language('ita'), Language('fra'),
                     Language('ron'), Language('nld'), Language('eng'), Language('deu'), Language('ell'),
                     Language('por', 'BR'), Language('bul'), Language('por'), Language('msa')}
        matches = {frozenset(['series', 'resolution', 'season']),
                   frozenset(['series', 'episode', 'season', 'title']),
                   frozenset(['series', 'release_group', 'season']),
                   frozenset(['series', 'episode', 'season', 'release_group', 'title']),
                   frozenset(['series', 'season']),
                   frozenset(['series', 'season', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season, video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_1(self):
        video = EPISODES[1]
        languages = {Language('ind'), Language('spa'), Language('hrv'), Language('ita'), Language('fra'),
                     Language('cat'), Language('ell'), Language('nld'), Language('eng'), Language('fas'),
                     Language('por'), Language('nor'), Language('deu'), Language('ron'), Language('por', 'BR'),
                     Language('bul')}
        matches = {frozenset(['series', 'episode', 'resolution', 'season', 'title', 'year']),
                   frozenset(['series', 'resolution', 'season', 'year']),
                   frozenset(['series', 'resolution', 'season', 'year', 'format']),
                   frozenset(['series', 'episode', 'season', 'title', 'year']),
                   frozenset(['series', 'episode', 'season', 'title', 'year', 'format']),
                   frozenset(['series', 'release_group', 'season', 'year']),
                   frozenset(['series', 'release_group', 'season', 'year', 'format']),
                   frozenset(['series', 'resolution', 'release_group', 'season', 'year']),
                   frozenset(['series', 'resolution', 'release_group', 'season', 'year', 'format']),
                   frozenset(['series', 'episode', 'season', 'release_group', 'title', 'year', 'format']),
                   frozenset(['series', 'season', 'year']),
                   frozenset(['series', 'season', 'year', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season, video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_year(self):
        video_no_year = EPISODES[2]
        video_year = EPISODES[3]
        with self.Provider() as provider:
            subtitles_no_year = provider.query(video_no_year.series, video_no_year.season, video_no_year.year)
            subtitles_year = provider.query(video_year.series, video_year.season, video_year.year)
        self.assertNotEqual(subtitles_no_year, subtitles_year)

    def test_list_subtitles(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['series', 'episode', 'season', 'release_group', 'title']),
                   frozenset(['series', 'episode', 'season', 'title'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('fra')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            provider.download_subtitle(subtitles[0])
        self.assertIsNotNone(subtitles[0].content)
        self.assertTrue(subtitles[0].is_valid)


class OpenSubtitlesProviderTestCase(ProviderTestCase):
    provider_name = 'opensubtitles'

    def test_query_movie_0_query(self):
        video = MOVIES[0]
        languages = {Language('eng')}
        matches = {frozenset([]),
                   frozenset(['imdb_id', 'resolution', 'title', 'year']),
                   frozenset(['imdb_id', 'resolution', 'title', 'year', 'format']),
                   frozenset(['imdb_id', 'title', 'year']),
                   frozenset(['imdb_id', 'title', 'year', 'format']),
                   frozenset(['imdb_id', 'video_codec', 'title', 'year', 'format']),
                   frozenset(['imdb_id', 'resolution', 'title', 'video_codec', 'year', 'format']),
                   frozenset(['imdb_id', 'title', 'year', 'video_codec', 'resolution', 'release_group', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, query=video.title)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_0_query(self):
        video = EPISODES[0]
        languages = {Language('eng')}
        matches = {frozenset(['series', 'episode', 'season', 'imdb_id', 'format']),
                   frozenset(['series', 'imdb_id', 'video_codec', 'episode', 'season', 'format']),
                   frozenset(['episode', 'title', 'series', 'imdb_id', 'video_codec', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, query=os.path.split(video.name)[1])
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_year(self):
        video_no_year = EPISODES[2]
        video_year = EPISODES[3]
        languages = {Language('eng')}
        with self.Provider() as provider:
            subtitles_no_year = provider.query(languages, query=os.path.split(video_no_year.name)[1])
            subtitles_year = provider.query(languages, query=os.path.split(video_year.name)[1])
        self.assertNotEqual(subtitles_no_year, subtitles_year)

    def test_query_episode_1_query(self):
        video = EPISODES[1]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['episode', 'title', 'series', 'imdb_id', 'video_codec', 'season', 'year', 'format']),
                   frozenset(['series', 'imdb_id', 'video_codec', 'episode', 'season', 'year']),
                   frozenset(['episode', 'video_codec', 'series', 'imdb_id', 'resolution', 'season', 'year']),
                   frozenset(['series', 'imdb_id', 'resolution', 'episode', 'season', 'year']),
                   frozenset(['series', 'episode', 'season', 'imdb_id', 'year']),
                   frozenset(['series', 'episode', 'season', 'imdb_id', 'year', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, query=os.path.split(video.name)[1])
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_movie_0_imdb_id(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['imdb_id', 'video_codec', 'title', 'year', 'format']),
                   frozenset(['imdb_id', 'resolution', 'title', 'video_codec', 'year']),
                   frozenset(['imdb_id', 'resolution', 'title', 'video_codec', 'year', 'format']),
                   frozenset(['imdb_id', 'title', 'year', 'video_codec', 'resolution', 'release_group', 'format']),
                   frozenset(['imdb_id', 'title', 'year']),
                   frozenset(['imdb_id', 'title', 'year', 'format']),
                   frozenset(['imdb_id', 'resolution', 'title', 'year']),
                   frozenset(['imdb_id', 'resolution', 'title', 'year', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, imdb_id=video.imdb_id)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_0_imdb_id(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['series', 'episode', 'season', 'imdb_id', 'format']),
                   frozenset(['episode', 'release_group', 'video_codec', 'series', 'imdb_id', 'resolution', 'season', 'format']),
                   frozenset(['series', 'imdb_id', 'video_codec', 'episode', 'season', 'format']),
                   frozenset(['episode', 'title', 'series', 'imdb_id', 'video_codec', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, imdb_id=video.imdb_id)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_movie_0_hash(self):
        video = MOVIES[0]
        languages = {Language('eng')}
        matches = {frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'imdb_id', 'format']),
                   frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'release_group', 'imdb_id', 'format']),
                   frozenset(['year', 'video_codec', 'imdb_id', 'hash', 'title', 'format']),
                   frozenset([]),
                   frozenset(['year', 'resolution', 'imdb_id', 'hash', 'title', 'format']),
                   frozenset(['year', 'imdb_id', 'hash', 'title']),
                   frozenset(['year', 'imdb_id', 'hash', 'title', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, hash=video.hashes['opensubtitles'], size=video.size)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_0_hash(self):
        video = EPISODES[0]
        languages = {Language('eng')}
        matches = {frozenset(['series', 'hash', 'format']),
                   frozenset(['episode', 'season', 'series', 'imdb_id', 'video_codec', 'hash', 'format']),
                   frozenset(['series', 'episode', 'season', 'hash', 'imdb_id', 'format']),
                   frozenset(['series', 'resolution', 'hash', 'video_codec', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, hash=video.hashes['opensubtitles'], size=video.size)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_list_subtitles(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['title', 'video_codec', 'year', 'resolution', 'release_group', 'imdb_id', 'format']),
                   frozenset(['imdb_id', 'year', 'title']),
                   frozenset(['imdb_id', 'year', 'title', 'format']),
                   frozenset(['year', 'video_codec', 'imdb_id', 'resolution', 'title']),
                   frozenset(['year', 'video_codec', 'imdb_id', 'resolution', 'title', 'format']),
                   frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'release_group', 'imdb_id', 'format']),
                   frozenset(['year', 'video_codec', 'imdb_id', 'hash', 'title', 'format']),
                   frozenset([]),
                   frozenset(['year', 'resolution', 'imdb_id', 'hash', 'title', 'format']),
                   frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'imdb_id', 'format']),
                   frozenset(['year', 'imdb_id', 'hash', 'title']),
                   frozenset(['year', 'imdb_id', 'hash', 'title', 'format']),
                   frozenset(['video_codec', 'imdb_id', 'year', 'title', 'format']),
                   frozenset(['year', 'imdb_id', 'resolution', 'title']),
                   frozenset(['year', 'imdb_id', 'resolution', 'title', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            provider.download_subtitle(subtitles[0])
        self.assertIsNotNone(subtitles[0].content)
        self.assertTrue(subtitles[0].is_valid)


class PodnapisiProviderTestCase(ProviderTestCase):
    provider_name = 'podnapisi'

    def test_query_movie_0(self):
        video = MOVIES[0]
        language = Language('eng')
        matches = {frozenset(['video_codec', 'title', 'resolution', 'year']),
                   frozenset(['title', 'resolution', 'year']),
                   frozenset(['video_codec', 'title', 'year']),
                   frozenset(['title', 'year']),
                   frozenset(['title']),
                   frozenset(['video_codec', 'title', 'resolution', 'release_group', 'year', 'format']),
                   frozenset(['video_codec', 'title', 'resolution', 'audio_codec', 'year', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, title=video.title, year=video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_query_episode_0(self):
        video = EPISODES[0]
        language = Language('eng')
        matches = {frozenset(['episode', 'series', 'season', 'video_codec', 'resolution', 'release_group', 'format']),
                   frozenset(['season', 'video_codec', 'episode', 'resolution', 'series'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, series=video.series, season=video.season, episode=video.episode,
                                       year=video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_query_episode_1(self):
        video = EPISODES[1]
        language = Language('eng')
        matches = {frozenset(['episode', 'release_group', 'series', 'video_codec', 'resolution', 'season', 'year', 'format']),
                   frozenset(['episode', 'series', 'video_codec', 'resolution', 'season', 'year']),
                   frozenset(['season', 'video_codec', 'episode', 'series', 'year'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, series=video.series, season=video.season, episode=video.episode,
                                       year=video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_list_subtitles(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['video_codec', 'title', 'resolution', 'year']),
                   frozenset(['title', 'resolution', 'year']),
                   frozenset(['video_codec', 'title', 'year']),
                   frozenset(['video_codec', 'title', 'year', 'format']),
                   frozenset(['title', 'year']),
                   frozenset(['title']),
                   frozenset(['video_codec', 'title', 'resolution', 'release_group', 'year', 'format']),
                   frozenset(['video_codec', 'title', 'resolution', 'audio_codec', 'year', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            provider.download_subtitle(subtitles[0])
        self.assertIsNotNone(subtitles[0].content)
        self.assertTrue(subtitles[0].is_valid)


class TheSubDBProviderTestCase(ProviderTestCase):
    provider_name = 'thesubdb'

    def test_query_episode_0(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('spa'), Language('por')}
        matches = {frozenset(['hash'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.hashes['thesubdb'])
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_1(self):
        video = EPISODES[1]
        languages = {Language('eng'), Language('por')}
        matches = {frozenset(['hash'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.hashes['thesubdb'])
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_list_subtitles(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('por')}
        matches = {frozenset(['hash'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('por')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            provider.download_subtitle(subtitles[0])
            provider.download_subtitle(subtitles[1])
        self.assertIsNotNone(subtitles[0].content)
        self.assertTrue(subtitles[0].is_valid)


class TVsubtitlesProviderTestCase(ProviderTestCase):
    provider_name = 'tvsubtitles'

    def test_find_show_id(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('the big bang')
        self.assertEqual(show_id, 154)

    def test_find_show_id_ambiguous(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('new girl')
        self.assertEqual(show_id, 977)

    def test_find_show_id_no_dots(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('marvel\'s agents of s h i e l d')
        self.assertEqual(show_id, 1340)

    def test_find_show_id_no_year_dallas(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('dallas')
        self.assertEqual(show_id, 646)

    def test_find_show_id_no_year_house_of_cards(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('house of cards')
        self.assertEqual(show_id, 352)

    def test_find_show_id_year_dallas(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('dallas', 2012)
        self.assertEqual(show_id, 1127)

    def test_find_show_id_year_house_of_cards(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('house of cards', 2013)
        self.assertEqual(show_id, 1246)

    def test_find_show_id_error(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('the big gaming')
        self.assertIsNone(show_id)

    def test_find_episode_ids(self):
        with self.Provider() as provider:
            episode_ids = provider.find_episode_ids(154, 5)
        self.assertEqual(set(episode_ids.keys()), set(range(1, 25)))

    def test_query_episode_0(self):
        video = EPISODES[0]
        languages = {Language('fra'), Language('por'), Language('hun'), Language('ron'), Language('eng')}
        matches = {frozenset(['series', 'episode', 'season', 'video_codec', 'format']),
                   frozenset(['series', 'episode', 'season', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season, video.episode, video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_1(self):
        video = EPISODES[1]
        languages = {Language('fra'), Language('ell'), Language('ron'), Language('eng'), Language('hun'),
                     Language('por'), Language('por', 'BR'), Language('jpn')}
        matches = {frozenset(['series', 'episode', 'resolution', 'season', 'year']),
                   frozenset(['series', 'episode', 'season', 'video_codec', 'year']),
                   frozenset(['series', 'episode', 'season', 'year'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season, video.episode, video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_list_subtitles(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['series', 'episode', 'season', 'format'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = EPISODES[0]
        languages = {Language('hun')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            provider.download_subtitle(subtitles[0])
        self.assertIsNotNone(subtitles[0].content)
        self.assertTrue(subtitles[0].is_valid)


def suite():
    suite = TestSuite()
    suite.addTest(TestLoader().loadTestsFromTestCase(Addic7edProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(OpenSubtitlesProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(PodnapisiProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(TheSubDBProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(TVsubtitlesProviderTestCase))
    return suite


if __name__ == '__main__':
    TextTestRunner().run(suite())
