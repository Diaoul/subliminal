#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from unittest import TestCase, TestSuite, TestLoader, TextTestRunner
from babelfish import Language
from pkg_resources import iter_entry_points
from subliminal import PROVIDERS_ENTRY_POINT
from subliminal.subtitle import is_valid_subtitle
from subliminal.tests.common import MOVIES, EPISODES


class ProviderTestCase(TestCase):
    provider_name = ''

    def setUp(self):
        for provider_entry_point in iter_entry_points(PROVIDERS_ENTRY_POINT, self.provider_name):
            self.Provider = provider_entry_point.load()
            break


class Addic7edProviderTestCase(ProviderTestCase):
    provider_name = 'addic7ed'

    def test_find_show_id(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('The Big Bang')
        self.assertEqual(show_id, 126)

    def test_find_show_id_error(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('the big how i met your mother')
        self.assertIsNone(show_id)

    def test_get_show_ids(self):
        with self.Provider() as provider:
            show_ids = provider.get_show_ids()
        self.assertIn('the big bang theory', show_ids)
        self.assertEqual(show_ids['the big bang theory'], 126)

    def test_query_episode_0(self):
        video = EPISODES[0]
        languages = {Language('tur'), Language('rus'), Language('heb'), Language('ita'), Language('fra'),
                     Language('ron'), Language('nld'), Language('eng'), Language('deu'), Language('ell'),
                     Language('por', 'BR'), Language('bul')}
        matches = {frozenset(['episode', 'release_group', 'title', 'series', 'resolution', 'season']),
                   frozenset(['series', 'resolution', 'season']),
                   frozenset(['series', 'episode', 'season', 'title']),
                   frozenset(['series', 'release_group', 'season']),
                   frozenset(['series', 'episode', 'season', 'release_group', 'title']),
                   frozenset(['series', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_1(self):
        video = EPISODES[1]
        languages = {Language('ind'), Language('spa'), Language('hrv'), Language('ita'), Language('fra'),
                     Language('cat'), Language('ell'), Language('nld'), Language('eng'), Language('fas'),
                     Language('por'), Language('nor'), Language('deu'), Language('ron'), Language('por', 'BR'),
                     Language('bul')}
        matches = {frozenset(['series', 'episode', 'resolution', 'season', 'title']),
                   frozenset(['series', 'resolution', 'season']),
                   frozenset(['series', 'episode', 'season', 'title']),
                   frozenset(['series', 'release_group', 'season']),
                   frozenset(['series', 'resolution', 'release_group', 'season']),
                   frozenset(['series', 'episode', 'season', 'release_group', 'title']),
                   frozenset(['series', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

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
            subtitle_text = provider.download_subtitle(subtitles[0])
        self.assertTrue(is_valid_subtitle(subtitle_text))


class BierDopjeProviderTestCase(ProviderTestCase):
    provider_name = 'bierdopje'

    def test_find_show_id(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('The Big Bang')
        self.assertEqual(show_id, 9203)

    def test_find_show_id_error(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('the big how i met your mother')
        self.assertIsNone(show_id)

    def test_query_episode_0(self):
        video = EPISODES[0]
        language = Language('eng')
        matches = {frozenset(['series', 'video_codec', 'resolution', 'episode', 'season']),
                   frozenset(['season', 'video_codec', 'episode', 'series']),
                   frozenset(['episode', 'video_codec', 'season', 'series', 'resolution', 'release_group'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, video.season, video.episode, series=video.series)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_query_episode_1(self):
        video = EPISODES[1]
        language = Language('nld')
        matches = {frozenset(['series', 'video_codec', 'resolution', 'episode', 'season']),
                   frozenset(['season', 'video_codec', 'episode', 'series']),
                   frozenset(['series', 'episode', 'season']),
                   frozenset(['season', 'video_codec', 'episode', 'release_group', 'series']),
                   frozenset(['episode', 'video_codec', 'season', 'series', 'resolution', 'release_group'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, video.season, video.episode, series=video.series)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_query_episode_0_tvdb_id(self):
        video = EPISODES[0]
        language = Language('eng')
        matches = {frozenset(['video_codec', 'tvdb_id', 'episode', 'season', 'series']),
                   frozenset(['episode', 'video_codec', 'series', 'season', 'tvdb_id', 'resolution', 'release_group']),
                   frozenset(['episode', 'series', 'video_codec', 'tvdb_id', 'resolution', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, video.season, video.episode, tvdb_id=video.tvdb_id)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_list_subtitles(self):
        video = EPISODES[1]
        languages = {Language('eng'), Language('nld')}
        matches = {frozenset(['series', 'video_codec', 'tvdb_id', 'episode', 'season']),
                   frozenset(['episode', 'video_codec', 'season', 'series', 'tvdb_id', 'resolution', 'release_group']),
                   frozenset(['season', 'tvdb_id', 'episode', 'series']),
                   frozenset(['episode', 'video_codec', 'season', 'series', 'tvdb_id', 'resolution']),
                   frozenset(['episode', 'video_codec', 'season', 'series', 'tvdb_id', 'release_group'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('nld')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            subtitle_text = provider.download_subtitle(subtitles[0])
        self.assertTrue(is_valid_subtitle(subtitle_text))


class OpenSubtitlesProviderTestCase(ProviderTestCase):
    provider_name = 'opensubtitles'

    def test_query_movie_0_query(self):
        video = MOVIES[0]
        languages = {Language('eng')}
        matches = {frozenset([]), frozenset(['imdb_id', 'resolution', 'title', 'year']),
                   frozenset(['imdb_id', 'title', 'year']),
                   frozenset(['imdb_id', 'video_codec', 'title', 'year']),
                   frozenset(['imdb_id', 'resolution', 'title', 'video_codec', 'year']),
                   frozenset(['imdb_id', 'title', 'year', 'video_codec', 'resolution', 'release_group'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, query=video.title)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_0_query(self):
        video = EPISODES[0]
        languages = {Language('eng')}
        matches = {frozenset(['series', 'episode', 'season', 'imdb_id']),
                   frozenset(['series', 'imdb_id', 'video_codec', 'episode', 'season']),
                   frozenset(['episode', 'title', 'series', 'imdb_id', 'video_codec', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, query=video.name.split(os.sep)[-1])
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_1_query(self):
        video = EPISODES[1]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['episode', 'title', 'series', 'imdb_id', 'video_codec', 'season']),
                   frozenset(['series', 'imdb_id', 'title', 'episode', 'season']),
                   frozenset(['series', 'imdb_id', 'video_codec', 'episode', 'season']),
                   frozenset(['episode', 'video_codec', 'series', 'imdb_id', 'resolution', 'season']),
                   frozenset(['series', 'imdb_id', 'resolution', 'episode', 'season']),
                   frozenset(['series', 'episode', 'season', 'imdb_id'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, query=video.name.split(os.sep)[-1])
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_movie_0_imdb_id(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['imdb_id', 'video_codec', 'title', 'year']),
                   frozenset(['imdb_id', 'resolution', 'title', 'video_codec', 'year']),
                   frozenset(['imdb_id', 'title', 'year', 'video_codec', 'resolution', 'release_group']),
                   frozenset(['imdb_id', 'title', 'year']),
                   frozenset(['imdb_id', 'resolution', 'title', 'year'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, imdb_id=video.imdb_id)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_0_imdb_id(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['series', 'episode', 'season', 'imdb_id']),
                   frozenset(['episode', 'release_group', 'video_codec', 'series', 'imdb_id', 'resolution', 'season']),
                   frozenset(['series', 'imdb_id', 'video_codec', 'episode', 'season']),
                   frozenset(['episode', 'title', 'series', 'imdb_id', 'video_codec', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, imdb_id=video.imdb_id)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_movie_0_hash(self):
        video = MOVIES[0]
        languages = {Language('eng')}
        matches = {frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'imdb_id']),
                   frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'release_group', 'imdb_id']),
                   frozenset(['year', 'video_codec', 'imdb_id', 'hash', 'title']),
                   frozenset([]),
                   frozenset(['year', 'resolution', 'imdb_id', 'hash', 'title']),
                   frozenset(['year', 'imdb_id', 'hash', 'title'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, hash=video.hashes['opensubtitles'], size=video.size)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_0_hash(self):
        video = EPISODES[0]
        languages = {Language('eng')}
        matches = {frozenset(['series', 'hash']),
                   frozenset(['episode', 'season', 'series', 'imdb_id', 'video_codec', 'hash']),
                   frozenset(['series', 'episode', 'season', 'hash', 'imdb_id']),
                   frozenset(['series', 'resolution', 'hash', 'video_codec'])}
        with self.Provider() as provider:
            subtitles = provider.query(languages, hash=video.hashes['opensubtitles'], size=video.size)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_list_subtitles(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['title', 'video_codec', 'year', 'resolution', 'release_group', 'imdb_id']),
                   frozenset(['imdb_id', 'year', 'title']),
                   frozenset(['year', 'video_codec', 'imdb_id', 'resolution', 'title']),
                   frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'release_group', 'imdb_id']),
                   frozenset(['year', 'video_codec', 'imdb_id', 'hash', 'title']),
                   frozenset([]),
                   frozenset(['year', 'resolution', 'imdb_id', 'hash', 'title']),
                   frozenset(['hash', 'title', 'video_codec', 'year', 'resolution', 'imdb_id']),
                   frozenset(['year', 'imdb_id', 'hash', 'title']),
                   frozenset(['video_codec', 'imdb_id', 'year', 'title']),
                   frozenset(['year', 'imdb_id', 'resolution', 'title'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            subtitle_text = provider.download_subtitle(subtitles[0])
        self.assertTrue(is_valid_subtitle(subtitle_text))


class PodnapisiProviderTestCase(ProviderTestCase):
    provider_name = 'podnapisi'

    def test_query_movie_0(self):
        video = MOVIES[0]
        language = Language('eng')
        matches = {frozenset(['video_codec', 'title', 'resolution', 'year']),
                   frozenset(['title', 'resolution', 'year']),
                   frozenset(['video_codec', 'title', 'year']),
                   frozenset(['title', 'year']),
                   frozenset(['video_codec', 'title', 'resolution', 'release_group', 'year']),
                   frozenset(['video_codec', 'title', 'resolution', 'audio_codec', 'year'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, title=video.title, year=video.year)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_query_episode_0(self):
        video = EPISODES[0]
        language = Language('eng')
        matches = {frozenset(['episode', 'series', 'season', 'video_codec', 'resolution', 'release_group']),
                   frozenset(['season', 'video_codec', 'episode', 'resolution', 'series'])}
        with self.Provider() as provider:
            subtitles = provider.query(language, series=video.series, season=video.season, episode=video.episode)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, {language})

    def test_list_subtitles(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['video_codec', 'title', 'resolution', 'year']),
                   frozenset(['title', 'resolution', 'year']),
                   frozenset(['video_codec', 'title', 'year']),
                   frozenset(['title', 'year']),
                   frozenset(['video_codec', 'title', 'resolution', 'release_group', 'year']),
                   frozenset(['video_codec', 'title', 'resolution', 'audio_codec', 'year'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = MOVIES[0]
        languages = {Language('eng'), Language('fra')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            subtitle_text = provider.download_subtitle(subtitles[0])
        self.assertTrue(is_valid_subtitle(subtitle_text))


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
            subtitle_text = provider.download_subtitle(subtitles[0])
        self.assertTrue(is_valid_subtitle(subtitle_text))


class TVsubtitlesProviderTestCase(ProviderTestCase):
    provider_name = 'tvsubtitles'

    def test_find_show_id(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('The Big Bang')
        self.assertEqual(show_id, 154)

    def test_find_show_id_ambiguous(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('New Girl')
        self.assertEqual(show_id, 977)

    def test_find_show_id_no_dots(self):
        with self.Provider() as provider:
            show_id = provider.find_show_id('Marvel\'s Agents of S H I E L D')
        self.assertEqual(show_id, 1340)

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
        matches = {frozenset(['series', 'episode', 'season', 'video_codec']),
                   frozenset(['series', 'episode', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season, video.episode)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_query_episode_1(self):
        video = EPISODES[1]
        languages = {Language('fra'), Language('ell'), Language('ron'), Language('eng'), Language('hun'),
                     Language('por'), Language('por', 'BR')}
        matches = {frozenset(['series', 'episode', 'resolution', 'season']),
                   frozenset(['series', 'episode', 'season', 'video_codec']),
                   frozenset(['series', 'episode', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.query(video.series, video.season, video.episode)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_list_subtitles(self):
        video = EPISODES[0]
        languages = {Language('eng'), Language('fra')}
        matches = {frozenset(['series', 'episode', 'season'])}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
        self.assertEqual({frozenset(subtitle.compute_matches(video)) for subtitle in subtitles}, matches)
        self.assertEqual({subtitle.language for subtitle in subtitles}, languages)

    def test_download_subtitle(self):
        video = EPISODES[0]
        languages = {Language('hun')}
        with self.Provider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            subtitle_text = provider.download_subtitle(subtitles[0])
        self.assertTrue(is_valid_subtitle(subtitle_text))


def suite():
    suite = TestSuite()
    suite.addTest(TestLoader().loadTestsFromTestCase(Addic7edProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(BierDopjeProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(OpenSubtitlesProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(PodnapisiProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(TheSubDBProviderTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(TVsubtitlesProviderTestCase))
    return suite


if __name__ == '__main__':
    TextTestRunner().run(suite())
