import os

import pytest
import requests
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.refiners.tmdb import TMDBClient, refine
from subliminal.video import Episode, Movie

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'tmdb')),
)

#: TMDB subliminal test API key
TMDB_API_KEY = '3dac925d5d494853ea6ef9161011fbb3'


@pytest.fixture
def client() -> TMDBClient:
    return TMDBClient(apikey=TMDB_API_KEY)


def test_session() -> None:
    session = requests.Session()
    client = TMDBClient(session=session)
    assert client.session is session


def test_headers() -> None:
    client = TMDBClient(headers={'X-Test': 'Value'})
    assert 'X-Test' in client.session.headers
    assert client.session.headers['X-Test'] == 'Value'


def test_apikey() -> None:
    apikey = '000000000'
    client = TMDBClient(headers={'X-Test': 'Value'})
    client.apikey = apikey
    assert 'api_key' in client.session.params  # type: ignore[operator]
    assert client.session.params['api_key'] == apikey  # type: ignore[index,call-overload]


@pytest.mark.integration
@vcr.use_cassette
def test_search_movie(client: TMDBClient) -> None:
    data = client.search('Man of Steel', is_movie=True)
    assert len(data) >= 12
    movie = data[0]
    assert movie['id'] == 49521
    assert movie['release_date'] == '2013-06-12'


@pytest.mark.integration
@vcr.use_cassette
def test_search_movie_wrong_title(client: TMDBClient) -> None:
    data = client.search('Meen of Stal', is_movie=True)
    assert data == []


@pytest.mark.integration
@vcr.use_cassette
def test_search_movie_year(client: TMDBClient) -> None:
    data = client.search('Man of Steel', is_movie=True, year=2013)
    assert len(data) == 1


@pytest.mark.integration
@vcr.use_cassette
def test_search_movie_page(client: TMDBClient) -> None:
    data_p1 = client.search('James Bond', is_movie=True)
    assert len(data_p1) == 20
    movie_p1 = data_p1[0]

    data = client.search('James Bond', is_movie=True, page=2)
    assert len(data) == 20
    movie = data[0]
    assert movie['id'] != movie_p1['id']
    assert movie['title'] != movie_p1['title']


@pytest.mark.integration
@vcr.use_cassette
def test_search_series(client: TMDBClient) -> None:
    data = client.search('The Big Bang Theory', is_movie=False)
    assert len(data) >= 1
    series = data[0]
    assert series['id'] == 1418
    assert series['first_air_date'] == '2007-09-24'


@pytest.mark.integration
@vcr.use_cassette
def test_search_series_wrong_name(client: TMDBClient) -> None:
    data = client.search('The Bing Bag Theory', is_movie=False)
    assert not data


@pytest.mark.integration
@vcr.use_cassette
def test_get_movie_id(client: TMDBClient) -> None:
    id_ = client.get_id('Man of Steel', is_movie=True)
    assert id_ == 49521


@pytest.mark.integration
@vcr.use_cassette
def test_get_movie_id_failed(client: TMDBClient) -> None:
    id_ = client.get_id('Meen of Stal', is_movie=True)
    assert id_ is None


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_id(client: TMDBClient) -> None:
    id_ = client.get_id('The Big Bang Theory', is_movie=False)
    assert id_ == 1418


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_wrong_id(client: TMDBClient) -> None:
    id_ = client.get_id('The Bing Bag Theory', is_movie=False)
    assert id_ is None


def test_refine_no_apikey(movies: dict[str, Movie]) -> None:
    movie = Movie(movies['man_of_steel'].name, movies['man_of_steel'].title.lower())
    refine(movie)
    assert movie.tmdb_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode(episodes: dict[str, Episode]) -> None:
    episode = Episode(
        episodes['bbt_s07e05'].name,
        episodes['bbt_s07e05'].series.lower(),
        episodes['bbt_s07e05'].season,
        episodes['bbt_s07e05'].episode,
    )
    refine(episode, apikey=TMDB_API_KEY)
    assert episode.series == episodes['bbt_s07e05'].series
    assert episode.year == episodes['bbt_s07e05'].year
    assert episode.series_imdb_id == episodes['bbt_s07e05'].series_imdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_original_series(episodes: dict[str, Episode]) -> None:
    episode = Episode(
        episodes['dallas_s01e03'].name,
        episodes['dallas_s01e03'].series.lower(),
        episodes['dallas_s01e03'].season,
        episodes['dallas_s01e03'].episode,
    )
    refine(episode, apikey=TMDB_API_KEY)
    assert episode.series == episodes['dallas_s01e03'].series
    assert episode.year == 1978
    assert episode.series_imdb_id == 'tt0077000'


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_year(episodes: dict[str, Episode]) -> None:
    episode = Episode(
        episodes['dallas_2012_s01e03'].name,
        episodes['dallas_2012_s01e03'].series.lower(),
        episodes['dallas_2012_s01e03'].season,
        episodes['dallas_2012_s01e03'].episode,
        year=episodes['dallas_2012_s01e03'].year,
        original_series=False,
    )
    refine(episode, apikey=TMDB_API_KEY)
    assert episode.series == episodes['dallas_2012_s01e03'].series
    assert episode.year == episodes['dallas_2012_s01e03'].year
    assert episode.series_imdb_id == 'tt1723760'


@pytest.mark.integration
@vcr.use_cassette
def test_refine_movie(movies: dict[str, Movie]) -> None:
    movie = Movie(movies['man_of_steel'].name, movies['man_of_steel'].title.lower())
    refine(movie, apikey=TMDB_API_KEY)
    assert movie.title == movies['man_of_steel'].title
    assert movie.year == movies['man_of_steel'].year
    assert movie.imdb_id == movies['man_of_steel'].imdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_movie_guess_alternative_title(movies: dict[str, Movie]) -> None:
    movie = Movie.fromname(movies['jack_reacher_never_go_back'].name)
    refine(movie, apikey=TMDB_API_KEY)
    assert movie.title == movies['jack_reacher_never_go_back'].title
    assert movie.year == movies['jack_reacher_never_go_back'].year
    assert movie.imdb_id == movies['jack_reacher_never_go_back'].imdb_id


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_with_country(episodes: dict[str, Episode]) -> None:
    episode = Episode.fromname(episodes['shameless_us_s08e01'].name)
    refine(episode, apikey=TMDB_API_KEY)
    # omdb has no country info. No match
    assert episode.series == episodes['shameless_us_s08e01'].series
    assert episode.series_tmdb_id == 34307
    assert episode.series_imdb_id == 'tt1586680'


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_with_country_hoc_us(episodes: dict[str, Episode]) -> None:
    episode = Episode.fromname(episodes['house_of_cards_us_s06e01'].name)
    refine(episode, apikey=TMDB_API_KEY)
    # omdb has no country info. No match
    assert episode.series == episodes['house_of_cards_us_s06e01'].series
    assert episode.series_tmdb_id == 1425
    assert episode.series_imdb_id == 'tt1856010'
