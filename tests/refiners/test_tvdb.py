import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.refiners.tvdb import TVDBClient, refine, series_re
from subliminal.video import Episode

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'tvdb')),
)


@pytest.fixture
def client() -> TVDBClient:
    return TVDBClient()


def test_apikey() -> None:
    apikey = '000000000'
    client = TVDBClient()
    client.apikey = apikey
    assert client.token is None


def test_series_re_no_year() -> None:
    m = series_re.match('Series Name')
    assert m
    groups = m.groupdict()
    assert groups['series'] == 'Series Name'
    assert groups['year'] is None


def test_series_re_year_parenthesis() -> None:
    m = series_re.match('Series Name (2013)')
    assert m
    groups = m.groupdict()
    assert groups['series'] == 'Series Name'
    assert groups['year'] == '2013'
    assert groups['country'] is None


def test_series_re_text_parenthesis() -> None:
    m = series_re.match('Series Name (Rock)')
    assert m
    groups = m.groupdict()
    assert groups['series'] == 'Series Name (Rock)'
    assert groups['year'] is None
    assert groups['country'] is None


def test_series_re_text_unclosed_parenthesis() -> None:
    m = series_re.match('Series Name (2013')
    assert m
    groups = m.groupdict()
    assert groups['series'] == 'Series Name (2013'
    assert groups['year'] is None
    assert groups['country'] is None


def test_series_re_country() -> None:
    m = series_re.match('Series Name (UK)')
    assert m
    groups = m.groupdict()
    assert groups['series'] == 'Series Name'
    assert groups['year'] is None
    assert groups['country'] == 'UK'


def test_language() -> None:
    client = TVDBClient()
    assert 'Accept-Language' in client.session.headers
    assert client.session.headers['Accept-Language'] == 'en'
    assert client.language == 'en'
    client.language = 'fr'
    assert client.session.headers['Accept-Language'] == 'fr'
    assert client.language == 'fr'


def test_session() -> None:
    session = requests.Session()
    client = TVDBClient(session=session)
    assert client.session is session


def test_headers() -> None:
    client = TVDBClient(headers={'X-Test': 'Value'})
    assert 'X-Test' in client.session.headers
    assert client.session.headers['X-Test'] == 'Value'


@pytest.mark.integration
@vcr.use_cassette
def test_login_error() -> None:
    client = TVDBClient('1234')
    with pytest.raises(requests.HTTPError):
        client.login()


@pytest.mark.integration
@vcr.use_cassette
def test_login(client: TVDBClient) -> None:
    assert client.token is None
    assert client.token_date <= datetime.now(timezone.utc) - timedelta(hours=1)
    assert client.token_expired
    client.login()
    assert client.token is not None
    assert client.token_date > datetime.now(timezone.utc) - timedelta(seconds=1)
    assert client.token_expired is False


@pytest.mark.integration
@vcr.use_cassette
def test_token_needs_refresh(client: TVDBClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, 'refresh_token_every', timedelta(milliseconds=100))
    assert client.token_needs_refresh
    client.login()
    assert not client.token_needs_refresh
    time.sleep(0.5)
    assert client.token_needs_refresh


@pytest.mark.integration
@vcr.use_cassette
def test_refresh_token(client: TVDBClient) -> None:
    client.login()
    old_token = client.token
    time.sleep(0.5)
    client.refresh_token()
    assert client.token != old_token


@pytest.mark.integration
@vcr.use_cassette
def test_search_series(client: TVDBClient) -> None:
    data = client.search_series('The Big Bang Theory')
    assert len(data) == 1
    series = data[0]
    assert series['id'] == 80379
    assert series['firstAired'] == '2007-09-24'


@pytest.mark.integration
@vcr.use_cassette
def test_search_series_wrong_name(client: TVDBClient) -> None:
    data = client.search_series('The Bing Bag Theory')
    assert data == {}


@pytest.mark.integration
@vcr.use_cassette
def test_get_series(client: TVDBClient) -> None:
    series = client.get_series(80379)
    assert series['id'] == 80379
    assert series['firstAired'] == '2007-09-24'
    assert series['imdbId'] == 'tt0898266'


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_wrong_id(client: TVDBClient) -> None:
    series = client.get_series(999999999)
    assert series == {}


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_actors(client: TVDBClient) -> None:
    actors = client.get_series_actors(80379)
    assert len(actors) == 12
    assert 'Jim Parsons' in {a['name'] for a in actors}


@pytest.mark.integration
@vcr.use_cassette
def test_get_series_actors_wrong_id(client: TVDBClient) -> None:
    actors = client.get_series_actors(999999999)
    assert actors == []


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_episodes(client: TVDBClient) -> None:
    episodes_data = client.query_series_episodes(80379, aired_season=7, aired_episode=5)
    assert episodes_data['links']['first'] == 1
    assert episodes_data['links']['last'] == 1
    assert episodes_data['links']['next'] is None
    assert episodes_data['links']['prev'] is None
    assert len(episodes_data['data']) == 1
    assert episodes_data['data'][0]['episodeName'] == 'The Workplace Proximity'


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_episodes_wrong_season(client: TVDBClient) -> None:
    episodes_data = client.query_series_episodes(80379, aired_season=99)
    assert episodes_data == {}


@pytest.mark.integration
@vcr.use_cassette
def test_refine(episodes: dict[str, Episode]) -> None:
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
def test_refine_episode_partial(episodes: dict[str, Episode]) -> None:
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
def test_refine_ambiguous(episodes: dict[str, Episode]) -> None:
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
def test_refine_ambiguous_2(episodes: dict[str, Episode]) -> None:
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
def test_refine_episode_year(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_2012_s01e03']
    episode = Episode(
        video.name.lower(),
        video.series.lower(),
        video.season,
        video.episode,
        year=video.year,
        original_series=video.original_series,
    )
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
def test_refine_episode_no_year(episodes: dict[str, Episode]) -> None:
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
def test_refine_episode_alternative_series(episodes: dict[str, Episode]) -> None:
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


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_with_comma(episodes: dict[str, Episode]) -> None:
    video = episodes['alex_inc_s01e04']
    episode = Episode.fromname(video.name)
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


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_with_country(episodes: dict[str, Episode]) -> None:
    video = episodes['shameless_us_s08e01']
    episode = Episode.fromname(video.name)
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


@pytest.mark.integration
@vcr.use_cassette
def test_refine_episode_with_country_hoc_us(episodes: dict[str, Episode]) -> None:
    video = episodes['house_of_cards_us_s06e01']
    episode = Episode.fromname(video.name)
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
