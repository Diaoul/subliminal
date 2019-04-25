# -*- coding: utf-8 -*-
import os

import pytest
import requests
from vcr import VCR

from subliminal.video import Episode, Movie
from subliminal.refiners.omdb import OMDBClient, refine


APIKEY = '00000000'

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'omdb')))


@pytest.fixture()
def client():
    return OMDBClient()


def test_session():
    session = requests.Session()
    client = OMDBClient(session=session)
    assert client.session is session


def test_headers():
    client = OMDBClient(headers={'X-Test': 'Value'})
    assert 'X-Test' in client.session.headers
    assert client.session.headers['X-Test'] == 'Value'


@pytest.mark.integration
@vcr.use_cassette
def test_get_id(client):
    data = client.get('tt0770828')
    assert data['Title'] == 'Man of Steel'


@pytest.mark.integration
@vcr.use_cassette
def test_get_wrong_id(client):
    data = client.get('tt9999999')
    assert data is None


@pytest.mark.integration
@vcr.use_cassette
def test_get_title(client):
    data = client.get(title='Man of Steel')
    assert data['imdbID'] == 'tt0770828'


@pytest.mark.integration
@vcr.use_cassette
def test_get_wrong_title(client):
    data = client.get(title='Meen of Stal')
    assert data is None


@pytest.mark.integration
@vcr.use_cassette
def test_search(client):
    data = client.search('Man of Steel')
    assert data['totalResults'] == '23'
    assert len(data['Search']) == 10
    assert data['Search'][0]['imdbID'] == 'tt0770828'
    assert data['Search'][0]['Year'] == '2013'


@pytest.mark.integration
@vcr.use_cassette
def test_search_wrong_title(client):
    data = client.search('Meen of Stal')
    assert data is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_type(client):
    data = client.search('Man of Steel', type='movie')
    assert data['totalResults'] == '21'


@pytest.mark.integration
@vcr.use_cassette
def test_search_year(client):
    data = client.search('Man of Steel', year=2013)
    assert data['totalResults'] == '13'


@pytest.mark.integration
@vcr.use_cassette
def test_search_page(client):
    data = client.search('Man of Steel', page=3)
    assert data['totalResults'] == '23'
    assert len(data['Search']) == 3
    assert data['Search'][0]['imdbID'] == 'tt5369598'
    assert data['Search'][0]['Title'] == 'BigHead Man of Steel'


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode(episodes):
    episode = Episode(episodes['bbt_s07e05'].name, episodes['bbt_s07e05'].series.lower(), episodes['bbt_s07e05'].season,
                      episodes['bbt_s07e05'].episode)
    refine(episode, apikey=APIKEY)
    assert episode.series == episodes['bbt_s07e05'].series
    assert episode.year == episodes['bbt_s07e05'].year
    assert episode.series_imdb_id == episodes['bbt_s07e05'].series_imdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_original_series(episodes):
    episode = Episode(episodes['dallas_s01e03'].name, episodes['dallas_s01e03'].series.lower(),
                      episodes['dallas_s01e03'].season, episodes['dallas_s01e03'].episode)
    refine(episode, apikey=APIKEY)
    assert episode.series == episodes['dallas_s01e03'].series
    assert episode.year == 1978
    assert episode.series_imdb_id == 'tt0077000'


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_year(episodes):
    episode = Episode(episodes['dallas_2012_s01e03'].name, episodes['dallas_2012_s01e03'].series.lower(),
                      episodes['dallas_2012_s01e03'].season, episodes['dallas_2012_s01e03'].episode,
                      year=episodes['dallas_2012_s01e03'].year, original_series=False)
    refine(episode, apikey=APIKEY)
    assert episode.series == episodes['dallas_2012_s01e03'].series
    assert episode.year == episodes['dallas_2012_s01e03'].year
    assert episode.series_imdb_id == 'tt1723760'


@pytest.mark.integration
@vcr.use_cassette
def test_refine_movie(movies):
    movie = Movie(movies['man_of_steel'].name, movies['man_of_steel'].title.lower())
    refine(movie, apikey=APIKEY)
    assert movie.title == movies['man_of_steel'].title
    assert movie.year == movies['man_of_steel'].year
    assert movie.imdb_id == movies['man_of_steel'].imdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_movie_guess_alternative_title(movies):
    movie = Movie.fromname(movies['jack_reacher_never_go_back'].name)
    refine(movie, apikey=APIKEY)
    assert movie.title == movies['jack_reacher_never_go_back'].title
    assert movie.year == movies['jack_reacher_never_go_back'].year
    assert movie.imdb_id == movies['jack_reacher_never_go_back'].imdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_with_country(episodes):
    episode = Episode.fromname(episodes['shameless_us_s08e01'].name)
    video_series = episode.series
    refine(episode, apikey=APIKEY)
    # omdb has no country info. No match
    assert episode.series == video_series
    assert episode.series_imdb_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_with_country_hoc_us(episodes):
    episode = Episode.fromname(episodes['house_of_cards_us_s06e01'].name)
    video_series = episode.series
    refine(episode, apikey=APIKEY)
    # omdb has no country info. No match
    assert episode.series == video_series
    assert episode.series_imdb_id is None
