#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import shutil
from unittest import TestCase, TestSuite, TestLoader, TextTestRunner
from babelfish import Language
from subliminal import list_subtitles, download_subtitles, download_best_subtitles
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
        self.assertTrue(len(subtitles) == len(videos))
        self.assertTrue(len(subtitles[videos[0]]) > 0)

    def test_list_subtitles_movie_0_por_br(self):
        videos = [MOVIES[0]]
        languages = {Language('por', 'BR')}
        subtitles = list_subtitles(videos, languages)
        self.assertTrue(len(subtitles) == len(videos))
        self.assertTrue(len(subtitles[videos[0]]) > 0)

    def test_list_subtitles_episodes(self):
        videos = [EPISODES[0], EPISODES[1]]
        languages = {Language('eng'), Language('fra')}
        subtitles = list_subtitles(videos, languages)
        self.assertTrue(len(subtitles) == len(videos))
        self.assertTrue(len(subtitles[videos[0]]) > 0)

    def test_download_subtitles(self):
        videos = [EPISODES[0], EPISODES[1]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, video.name.split(os.sep)[-1])
        languages = {Language('eng'), Language('fra')}
        subtitles = list_subtitles(videos, languages)
        download_subtitles(subtitles)
        for video in videos:
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.en.srt'))
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.fr.srt'))

    def test_download_subtitles_single(self):
        videos = [EPISODES[0], EPISODES[1]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, video.name.split(os.sep)[-1])
        languages = {Language('eng'), Language('fra')}
        subtitles = list_subtitles(videos, languages)
        download_subtitles(subtitles, single=True)
        for video in videos:
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.srt'))

    def test_download_best_subtitles(self):
        videos = [EPISODES[0], EPISODES[1]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, video.name.split(os.sep)[-1])
        languages = {Language('eng'), Language('fra')}
        subtitles = download_best_subtitles(videos, languages)
        for video in videos:
            self.assertTrue(video in subtitles and len(subtitles[video]) == 2)
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.en.srt'))
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.fr.srt'))

    def test_download_best_subtitles_single(self):
        videos = [EPISODES[0], EPISODES[1]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, video.name.split(os.sep)[-1])
        languages = {Language('eng'), Language('fra')}
        subtitles = download_best_subtitles(videos, languages, single=True)
        for video in videos:
            self.assertTrue(video in subtitles and len(subtitles[video]) == 1)
            self.assertTrue(os.path.exists(os.path.splitext(video.name)[0] + '.srt'))

    def test_download_best_subtitles_min_score(self):
        videos = [MOVIES[0]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, video.name.split(os.sep)[-1])
        languages = {Language('eng'), Language('fra')}
        subtitles = download_best_subtitles(videos, languages, min_score=1000)
        self.assertTrue(len(subtitles) == 0)

    def test_download_best_subtitles_hearing_impaired(self):
        videos = [MOVIES[0]]
        for video in videos:
            video.name = os.path.join(TEST_DIR, video.name.split(os.sep)[-1])
        languages = {Language('eng')}
        subtitles = download_best_subtitles(videos, languages, hearing_impaired=True)
        self.assertTrue(subtitles[videos[0]][0].hearing_impaired == True)


def suite():
    suite = TestSuite()
    suite.addTest(TestLoader().loadTestsFromTestCase(ApiTestCase))
    return suite


if __name__ == '__main__':
    TextTestRunner().run(suite())
