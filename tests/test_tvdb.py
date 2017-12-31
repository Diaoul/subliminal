# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import os
import time

import pytest
import requests
from vcr import VCR

from subliminal import __short_version__
from subliminal.video import Episode
from subliminal.refiners.tvdb import TVDBClient, refine, series_re

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'tvdb')))


@pytest.fixture()
def client():
    return TVDBClient('2AE5D1E42E7194B9', headers={'User-Agent': 'Subliminal/%s' % __short_version__})


def test_series_re_no_year():
    groups = series_re.match('Series Name').groupdict()
    assert groups['series'] == 'Series Name'
    assert groups['year'] is None


def test_series_re_year_parenthesis():
    groups = series_re.match('Series Name (2013)').groupdict()
    assert groups['series'] == 'Series Name'
    assert groups['year'] == '2013'
    assert groups['country'] is None


def test_series_re_text_parenthesis():
    groups = series_re.match('Series Name (Rock)').groupdict()
    assert groups['series'] == 'Series Name (Rock)'
    assert groups['year'] is None
    assert groups['country'] is None


def test_series_re_text_unclosed_parenthesis():
    groups = series_re.match('Series Name (2013').groupdict()
    assert groups['series'] == 'Series Name (2013'
    assert groups['year'] is None
    assert groups['country'] is None


def test_series_re_country():
    groups = series_re.match('Series Name (UK)').groupdict()
    assert groups['series'] == 'Series Name'
    assert groups['year'] is None
    assert groups['country'] == 'UK'


def test_language():
    client = TVDBClient()
    assert 'Accept-Language' in client.session.headers
    assert client.session.headers['Accept-Language'] == 'en'
    assert client.language == 'en'
    client.language = 'fr'
    assert client.session.headers['Accept-Language'] == 'fr'
    assert client.language == 'fr'


def test_session():
    session = requests.Session()
    client = TVDBClient(session=session)
    assert client.session is session


def test_headers():
    client = TVDBClient(headers={'X-Test': 'Value'})
    assert 'X-Test' in client.session.headers
    assert client.session.headers['X-Test'] == 'Value'


@pytest.mark.integration
@vcr.use_cassette
def test_login_error():
    client = TVDBClient('1234', headers={'User-Agent': 'Subliminal/%s' % __short_version__})
    with pytest.raises(requests.HTTPError):
        client.login()


@pytest.mark.integration
@vcr.use_cassette
def test_login(client):
    assert client.token is None
    assert client.token_date <= datetime.utcnow() - timedelta(hours=1)
    assert client.token_expired
    client.login()
    assert client.token is not None
    assert client.token_date > datetime.utcnow() - timedelta(seconds=1)
    assert client.token_expired is False


@pytest.mark.integration
@vcr.use_cassette
def test_token_needs_refresh(client, monkeypatch):
    monkeypatch.setattr(client, 'refresh_token_every', timedelta(milliseconds=100))
    assert client.token_needs_refresh
    client.login()
    assert not client.token_needs_refresh
    time.sleep(0.5)
    assert client.token_needs_refresh


@pytest.mark.integration
@vcr.use_cassette
def test_refresh_token(client):
    client.login()
    old_token = client.token
    time.sleep(0.5)
    client.refresh_token()
    assert client.token != old_token


@pytest.mark.integration
@vcr.use_cassette
def test_search_series(client):
    data = client.search_series('The Big Bang Theory')
    assert len(data) == 1
    series = data[0]
    assert series['id'] == 80379
    assert series['firstAired'] == '2007-09-24'


@pytest.mark.integration
@vcr.use_cassette
def test_search_series_wrong_name(client):
    data = client.search_series('The Bing Bag Theory')
    assert data is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_series_no_parameter(client):
    with pytest.raises(requests.HTTPError):
        client.search_series()


@pytest.mark.integration
@vcr.use_cassette
def test_search_series_multiple_parameters(client):
    with pytest.raises(requests.HTTPError):
        client.search_series('The Big Bang Theory', 'tt0898266')


@pytest.mark.integration
@vcr.use_cassette
def test_get_series(client):
    series = client.get_series(80379)
    assert series['id'] == 80379
    assert series['firstAired'] == '2007-09-24'
    assert series['imdbId'] == 'tt0898266'


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_wrong_id(client):
    series = client.get_series(999999999)
    assert series is None


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_actors(client):
    actors = client.get_series_actors(80379)
    assert len(actors) == 8
    assert 'Jim Parsons' in {a['name'] for a in actors}


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_actors_wrong_id(client):
    actors = client.get_series_actors(999999999)
    assert actors is None


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_episodes(client):
    episodes_data = client.get_series_episodes(80379)
    assert episodes_data['links']['first'] == 1
    assert episodes_data['links']['last'] == 3
    assert episodes_data['links']['next'] == 2
    assert episodes_data['links']['prev'] is None
    assert len(episodes_data['data']) == 100


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_episodes_page(client):
    episodes_data = client.get_series_episodes(80379, page=2)
    assert episodes_data['links']['first'] == 1
    assert episodes_data['links']['last'] == 3
    assert episodes_data['links']['next'] == 3
    assert episodes_data['links']['prev'] == 1
    assert len(episodes_data['data']) == 100


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_episodes_wrong_id(client):
    episodes_data = client.get_series_episodes(999999999)
    assert episodes_data is None


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_episodes_wrong_page(client):
    episodes_data = client.get_series_episodes(80379, page=10)
    assert episodes_data is None


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_episodes(client):
    episodes_data = client.query_series_episodes(80379, aired_season=7, aired_episode=5)
    assert episodes_data['links']['first'] == 1
    assert episodes_data['links']['last'] == 1
    assert episodes_data['links']['next'] is None
    assert episodes_data['links']['prev'] is None
    assert len(episodes_data['data']) == 1
    assert episodes_data['data'][0]['episodeName'] == 'The Workplace Proximity'


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_episodes_wrong_season(client):
    episodes_data = client.query_series_episodes(80379, aired_season=99)
    assert episodes_data is None


@pytest.mark.integration
@vcr.use_cassette
def test_refine(episodes):
    video = episodes['bbt_s07e05']
    episode = Episode(video.name.lower(), video.series.lower(), video.season, video.episode)
    refine(episode)
    assert episode.series == video.series
    assert episode.year == video.year
    assert episode.original_series == video.original_series
    assert episode.title == video.title
    assert episode.imdb_id == video.imdb_id
    assert episode.series_imdb_id == video.series_imdb_id
    assert episode.tvdb_id == video.tvdb_id
    assert episode.series_tvdb_id == video.series_tvdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_partial(episodes):
    video = episodes['csi_s15e18']
    episode = Episode(video.name.lower(), video.series.lower().split(':')[0], video.season, video.episode)
    refine(episode)
    assert episode.series == video.series
    assert episode.year == video.year
    assert episode.original_series == video.original_series
    assert episode.title == video.title
    assert episode.imdb_id == video.imdb_id
    assert episode.series_imdb_id == video.series_imdb_id
    assert episode.tvdb_id == video.tvdb_id
    assert episode.series_tvdb_id == video.series_tvdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_ambiguous(episodes):
    video = episodes['colony_s01e09']
    episode = Episode(video.name.lower(), video.series.lower(), video.season, video.episode)
    refine(episode)
    assert episode.series == video.series
    assert episode.year == video.year
    assert episode.original_series == video.original_series
    assert episode.title == video.title
    assert episode.imdb_id == video.imdb_id
    assert episode.series_imdb_id == video.series_imdb_id
    assert episode.tvdb_id == video.tvdb_id
    assert episode.series_tvdb_id == video.series_tvdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_ambiguous_2(episodes):
    video = episodes['the_100_s03e09']
    episode = Episode(video.name.lower(), video.series.lower(), video.season, video.episode)
    refine(episode)
    assert episode.series == video.series
    assert episode.year == video.year
    assert episode.original_series == video.original_series
    assert episode.title == video.title
    assert episode.imdb_id == video.imdb_id
    assert episode.series_imdb_id == video.series_imdb_id
    assert episode.tvdb_id == video.tvdb_id
    assert episode.series_tvdb_id == video.series_tvdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_year(episodes):
    video = episodes['dallas_2012_s01e03']
    episode = Episode(video.name.lower(), video.series.lower(), video.season, video.episode, year=video.year,
                      original_series=video.original_series)
    refine(episode)
    assert episode.series == video.series
    assert episode.year == video.year
    assert episode.original_series == video.original_series
    assert episode.title == video.title
    assert episode.imdb_id == video.imdb_id
    assert episode.series_imdb_id == video.series_imdb_id
    assert episode.tvdb_id == video.tvdb_id
    assert episode.series_tvdb_id == video.series_tvdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_no_year(episodes):
    video = episodes['dallas_s01e03']
    episode = Episode(video.name.lower(), video.series.lower(), video.season, video.episode)
    refine(episode)
    assert episode.series == video.series
    assert episode.year == video.year
    assert episode.original_series == video.original_series
    assert episode.title == video.title
    assert episode.imdb_id == video.imdb_id
    assert episode.series_imdb_id == video.series_imdb_id
    assert episode.tvdb_id == video.tvdb_id
    assert episode.series_tvdb_id == video.series_tvdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_alternative_series(episodes):
    video = episodes['turn_s04e03']
    episode = Episode(video.name.lower(), video.series.lower(), video.season, video.episode)
    refine(episode)
    assert episode.series == video.series
    assert episode.year == video.year
    assert episode.original_series == video.original_series
    assert episode.title == video.title
    assert episode.imdb_id == video.imdb_id
    assert episode.series_imdb_id == video.series_imdb_id
    assert episode.tvdb_id == video.tvdb_id
    assert episode.series_tvdb_id == video.series_tvdb_id
    assert episode.alternative_series == video.alternative_series
