import os

import pytest
import requests
from subliminal.refiners.omdb import OMDBClient, refine
from subliminal.video import Episode, Movie
from vcr import VCR  # type: ignore[import-untyped]

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'omdb')),
)


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


def test_apikey():
    apikey = '000000000'
    client = OMDBClient(headers={'X-Test': 'Value'})
    client.apikey = apikey
    assert 'apikey' in client.session.params  # type: ignore[operator]
    assert client.session.params['apikey'] == apikey  # type: ignore[index,call-overload]


@pytest.mark.integration()
@vcr.use_cassette
def test_get_id(client):
    data = client.search_by_id('tt0770828')
    assert data['Title'] == 'Man of Steel'


@pytest.mark.integration()
@vcr.use_cassette
def test_get_wrong_id(client):
    data = client.search_by_id('tt9999999')
    assert not data


@pytest.mark.integration()
@vcr.use_cassette
def test_get_title(client):
    data = client.search_by_title('Man of Steel')
    assert data['imdbID'] == 'tt0770828'


@pytest.mark.integration()
@vcr.use_cassette
def test_get_wrong_title(client):
    data = client.search_by_title('Meen of Stal')
    assert not data


@pytest.mark.integration()
@vcr.use_cassette
def test_search(client):
    data = client.search('Man of Steel')
    assert data['totalResults'] == '30'
    assert len(data['Search']) == 10
    assert data['Search'][0]['imdbID'] == 'tt0770828'
    assert data['Search'][0]['Year'] == '2013'


@pytest.mark.integration()
@vcr.use_cassette
def test_search_wrong_title(client):
    data = client.search('Meen of Stal')
    assert not data


@pytest.mark.integration()
@vcr.use_cassette
def test_search_type(client):
    data = client.search('Man of Steel', is_movie=True)
    assert data['totalResults'] == '28'


@pytest.mark.integration()
@vcr.use_cassette
def test_search_year(client):
    data = client.search('Man of Steel', year=2013)
    assert data['totalResults'] == '15'


@pytest.mark.integration()
@vcr.use_cassette
def test_search_page(client):
    data = client.search('Man of Steel', page=3)
    assert data['totalResults'] == '30'
    assert len(data['Search']) == 10
    assert data['Search'][0]['imdbID'] == 'tt2378339'
    assert data['Search'][0]['Title'] == 'Kurt Morrow: Man of Steel'


@pytest.mark.integration()
@vcr.use_cassette
def test_refine_episode(episodes):
    episode = Episode(
        episodes['bbt_s07e05'].name,
        episodes['bbt_s07e05'].series.lower(),
        episodes['bbt_s07e05'].season,
        episodes['bbt_s07e05'].episode,
    )
    refine(episode)
    assert episode.series == episodes['bbt_s07e05'].series
    assert episode.year == episodes['bbt_s07e05'].year
    assert episode.series_imdb_id == episodes['bbt_s07e05'].series_imdb_id


@pytest.mark.integration()
@vcr.use_cassette
def test_refine_episode_original_series(episodes):
    episode = Episode(
        episodes['dallas_s01e03'].name,
        episodes['dallas_s01e03'].series.lower(),
        episodes['dallas_s01e03'].season,
        episodes['dallas_s01e03'].episode,
    )
    refine(episode)
    assert episode.series == episodes['dallas_s01e03'].series
    assert episode.year == 1978
    assert episode.series_imdb_id == 'tt0077000'


@pytest.mark.integration()
@vcr.use_cassette
def test_refine_episode_year(episodes):
    episode = Episode(
        episodes['dallas_2012_s01e03'].name,
        episodes['dallas_2012_s01e03'].series.lower(),
        episodes['dallas_2012_s01e03'].season,
        episodes['dallas_2012_s01e03'].episode,
        year=episodes['dallas_2012_s01e03'].year,
        original_series=False,
    )
    refine(episode)
    assert episode.series == episodes['dallas_2012_s01e03'].series
    assert episode.year == episodes['dallas_2012_s01e03'].year
    assert episode.series_imdb_id == 'tt1723760'


@pytest.mark.integration()
@vcr.use_cassette
def test_refine_movie(movies):
    movie = Movie(movies['man_of_steel'].name, movies['man_of_steel'].title.lower())
    refine(movie)
    assert movie.title == movies['man_of_steel'].title
    assert movie.year == movies['man_of_steel'].year
    assert movie.imdb_id == movies['man_of_steel'].imdb_id


@pytest.mark.integration()
@vcr.use_cassette
def test_refine_movie_guess_alternative_title(movies):
    movie = Movie.fromname(movies['jack_reacher_never_go_back'].name)
    refine(movie)
    assert movie.title == movies['jack_reacher_never_go_back'].title
    assert movie.year == movies['jack_reacher_never_go_back'].year
    assert movie.imdb_id == movies['jack_reacher_never_go_back'].imdb_id


@pytest.mark.integration()
@vcr.use_cassette
def test_refine_episode_with_country(episodes):
    episode = Episode.fromname(episodes['shameless_us_s08e01'].name)
    video_series = episode.series
    refine(episode)
    # omdb has no country info. No match
    assert episode.series == video_series
    assert episode.series_imdb_id is None


@pytest.mark.integration()
@vcr.use_cassette
def test_refine_episode_with_country_hoc_us(episodes):
    episode = Episode.fromname(episodes['house_of_cards_us_s06e01'].name)
    video_series = episode.series
    refine(episode)
    # omdb has no country info. No match
    assert episode.series == video_series
    assert episode.series_imdb_id is None
