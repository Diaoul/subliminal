#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import shutil
from unittest import TestCase, TestSuite, TestLoader, TextTestRunner
from babelfish import Language
from subliminal import list_subtitles, download_subtitles, save_subtitles, download_best_subtitles, scan_video
from subliminal.tests.common import MOVIES, EPISODES


TEST_DIR = 'test_data'


class ApiTestCase(TestCase):
    def setUp(self):
        os.mkdir(TEST_DIR)

    def tearDown(self):
        shutil.rmtree(TEST_DIR)

    def test_list_subtitles_movie_0(self):
        videos = [MOVIES[0]]
        languages = {Language('eng')}
        subtitles = list_subtitles(videos, languages)
        self.assertEqual(len(subtitles), len(videos))
        self.assertGreater(len(subtitles[videos[0]]), 0)

    def test_list_subtitles_movie_0_por_br(self):
        videos = [MOVIES[0]]
        languages = {Language('por', 'BR')}
        subtitles = list_subtitles(videos, languages)
        self.assertEqual(len(subtitles), len(videos))
        self.assertGreater(len(subtitles[videos[0]]), 0)

    def test_list_subtitles_episodes(self):
        videos = [EPISODES[0], EPISODES[1]]
        languages = {Language('eng'), Language('fra')}
        subtitles = list_subtitles(videos, languages)
        self.assertEqual(len(subtitles), len(videos))
        self.assertGreater(len(subtitles[videos[0]]), 0)

    def test_download_subtitles(self):
        videos = [EPISODES[0]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, os.path.split(video.name)[1])
        languages = {Language('eng')}
        subtitles = list_subtitles(videos, languages)
        download_subtitles(subtitles[videos[0]][:5])
        self.assertGreaterEqual(len([s for s in subtitles[videos[0]] if s.content is not None]), 4)

    def test_download_best_subtitles(self):
        videos = [EPISODES[0], EPISODES[1]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, os.path.split(video.name)[1])
        languages = {Language('eng'), Language('fra')}
        subtitles = download_best_subtitles(videos, languages)
        for video in videos:
            self.assertIn(video, subtitles)
            self.assertEqual(len(subtitles[video]), 2)

    def test_save_subtitles(self):
        videos = [EPISODES[0], EPISODES[1]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, os.path.split(video.name)[1])
        languages = {Language('eng'), Language('fra')}
        subtitles = list_subtitles(videos, languages)

        # make a list of subtitles to download (one per language per video)
        subtitles_to_download = []
        for video, video_subtitles in subtitles.items():
            video_subtitle_languages = set()
            for video_subtitle in video_subtitles:
                if video_subtitle.language in video_subtitle_languages:
                    continue
                subtitles_to_download.append(video_subtitle)
                video_subtitle_languages.add(video_subtitle.language)
                if video_subtitle_languages == languages:
                    break
        self.assertEqual(len(subtitles_to_download), 4)

        # download
        download_subtitles(subtitles_to_download)
        save_subtitles(subtitles)
        for video in videos:
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.en.srt'))
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.fr.srt'))

    def test_save_subtitles_single(self):
        videos = [EPISODES[0], EPISODES[1]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, os.path.split(video.name)[1])
        languages = {Language('eng'), Language('fra')}
        subtitles = download_best_subtitles(videos, languages)
        save_subtitles(subtitles, single=True)
        for video in videos:
            self.assertIn(video, subtitles)
            self.assertEqual(len(subtitles[video]), 2)
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.srt'))

    def test_download_best_subtitles_min_score(self):
        videos = [MOVIES[0]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, os.path.split(video.name)[1])
        languages = {Language('eng'), Language('fra')}
        subtitles = download_best_subtitles(videos, languages, min_score=1000)
        self.assertEqual(len(subtitles), 0)

    def test_download_best_subtitles_hearing_impaired(self):
        videos = [MOVIES[0]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, os.path.split(video.name)[1])
        languages = {Language('eng')}
        subtitles = download_best_subtitles(videos, languages, hearing_impaired=True)
        self.assertTrue(subtitles[videos[0]][0].hearing_impaired)


class VideoTestCase(TestCase):
    def setUp(self):
        os.mkdir(TEST_DIR)
        for video in MOVIES + EPISODES:
            open(os.path.join(TEST_DIR, os.path.split(video.name)[1]), 'w').close()

    def tearDown(self):
        shutil.rmtree(TEST_DIR)

    def test_scan_video_movie(self):
        video = MOVIES[0]
        scanned_video = scan_video(os.path.join(TEST_DIR, os.path.split(video.name)[1]))
        self.assertEqual(scanned_video.name, os.path.join(TEST_DIR, os.path.split(video.name)[1]))
        self.assertEqual(scanned_video.title.lower(), video.title.lower())
        self.assertEqual(scanned_video.year, video.year)
        self.assertEqual(scanned_video.video_codec, video.video_codec)
        self.assertEqual(scanned_video.format, video.format)
        self.assertEqual(scanned_video.resolution, video.resolution)
        self.assertEqual(scanned_video.release_group, video.release_group)
        self.assertEqual(scanned_video.subtitle_languages, set())
        self.assertEqual(scanned_video.hashes, {})
        self.assertIsNone(scanned_video.audio_codec)
        self.assertIsNone(scanned_video.imdb_id)
        self.assertEqual(scanned_video.size, 0)

    def test_scan_video_episode(self):
        video = EPISODES[0]
        scanned_video = scan_video(os.path.join(TEST_DIR, os.path.split(video.name)[1]))
        self.assertEqual(scanned_video.name, os.path.join(TEST_DIR, os.path.split(video.name)[1]))
        self.assertEqual(scanned_video.series, video.series)
        self.assertEqual(scanned_video.season, video.season)
        self.assertEqual(scanned_video.episode, video.episode)
        self.assertEqual(scanned_video.video_codec, video.video_codec)
        self.assertEqual(scanned_video.format, video.format)
        self.assertEqual(scanned_video.resolution, video.resolution)
        self.assertEqual(scanned_video.release_group, video.release_group)
        self.assertEqual(scanned_video.subtitle_languages, set())
        self.assertEqual(scanned_video.hashes, {})
        self.assertIsNone(scanned_video.title)
        self.assertIsNone(scanned_video.tvdb_id)
        self.assertIsNone(scanned_video.imdb_id)
        self.assertIsNone(scanned_video.audio_codec)
        self.assertEqual(scanned_video.size, 0)

    def test_scan_video_subtitle_language_und(self):
        video = EPISODES[0]
        open(os.path.join(TEST_DIR, os.path.splitext(os.path.split(video.name)[1])[0]) + '.srt', 'w').close()
        scanned_video = scan_video(os.path.join(TEST_DIR, os.path.split(video.name)[1]))
        self.assertEqual(scanned_video.subtitle_languages, {Language('und')})

    def test_scan_video_subtitles_language_eng(self):
        video = EPISODES[0]
        open(os.path.join(TEST_DIR, os.path.splitext(os.path.split(video.name)[1])[0]) + '.en.srt', 'w').close()
        scanned_video = scan_video(os.path.join(TEST_DIR, os.path.split(video.name)[1]))
        self.assertEqual(scanned_video.subtitle_languages, {Language('eng')})

    def test_scan_video_subtitles_languages(self):
        video = EPISODES[0]
        open(os.path.join(TEST_DIR, os.path.splitext(os.path.split(video.name)[1])[0]) + '.en.srt', 'w').close()
        open(os.path.join(TEST_DIR, os.path.splitext(os.path.split(video.name)[1])[0]) + '.fr.srt', 'w').close()
        open(os.path.join(TEST_DIR, os.path.splitext(os.path.split(video.name)[1])[0]) + '.srt', 'w').close()
        scanned_video = scan_video(os.path.join(TEST_DIR, os.path.split(video.name)[1]))
        self.assertEqual(scanned_video.subtitle_languages, {Language('eng'), Language('fra'), Language('und')})


def suite():
    suite = TestSuite()
    suite.addTest(TestLoader().loadTestsFromTestCase(ApiTestCase))
    suite.addTest(TestLoader().loadTestsFromTestCase(VideoTestCase))
    return suite


if __name__ == '__main__':
    TextTestRunner().run(suite())
