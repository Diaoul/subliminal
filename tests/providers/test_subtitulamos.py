import logging
import os
from unittest.mock import patch

import pytest
from babelfish import Language, language_converters  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.exceptions import NotInitializedProviderError
from subliminal.providers.subtitulamos import SubtitulamosProvider, SubtitulamosSubtitle
from subliminal.video import Episode

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'subtitulamos')),
)

logger_name = 'subliminal.providers.subtitulamos'


@pytest.mark.converter
def test_converter_convert_alpha3() -> None:
    assert language_converters['subtitulamos'].convert('cat') == 'Català'


@pytest.mark.converter
def test_converter_convert_alpha3_country() -> None:
    assert language_converters['subtitulamos'].convert('spa', 'MX') == 'Español (Latinoamérica)'
    assert language_converters['subtitulamos'].convert('spa', 'AR') == 'Español (Latinoamérica)'
    assert language_converters['subtitulamos'].convert('por', 'BR') == 'Brazilian'


@pytest.mark.converter
def test_converter_convert_alpha3_name_converter() -> None:
    assert (
        language_converters['subtitulamos'].convert(
            'fra',
        )
        == 'French'
    )


@pytest.mark.converter
def test_converter_reverse() -> None:
    assert language_converters['subtitulamos'].reverse('Español') == ('spa', None, None)


@pytest.mark.converter
def test_converter_reverse_country() -> None:
    assert language_converters['subtitulamos'].reverse('Español (España)') == ('spa', None, None)
    assert language_converters['subtitulamos'].reverse('Español (Latinoamérica)') == ('spa', 'MX', None)


@pytest.mark.converter
def test_converter_reverse_name_converter() -> None:
    assert language_converters['subtitulamos'].reverse('French') == ('fra', None, None)


def test_get_matches_episode(episodes: dict[str, Episode]) -> None:
    subtitle = SubtitulamosSubtitle(
        language=Language('spa'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=11,
        episode=16,
        title='the neonatal nomenclature',
        year=2007,
        release_group='AVS/SVA',
    )

    matches = subtitle.get_matches(episodes['bbt_s11e16'])
    assert matches == {'release_group', 'series', 'year', 'country', 'episode', 'season', 'title'}


@pytest.mark.integration
@vcr.use_cassette
def test_login() -> None:
    provider = SubtitulamosProvider()
    assert provider.session is None
    provider.initialize()
    assert provider.session is not None


@pytest.mark.integration
@vcr.use_cassette
def test_logout() -> None:
    provider = SubtitulamosProvider()
    provider.initialize()
    provider.terminate()
    assert provider.session is None


@pytest.mark.integration
def test_logout_without_initialization() -> None:
    provider = SubtitulamosProvider()
    with pytest.raises(NotInitializedProviderError):
        provider.terminate()


@pytest.mark.integration
def test_list_subtitles_without_initialization(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s11e16']
    languages = {Language('eng'), Language('spa')}

    provider = SubtitulamosProvider()
    with pytest.raises(NotInitializedProviderError):
        provider.list_subtitles(video, languages)


@pytest.mark.integration
def test_list_subtitles_no_video_type() -> None:
    video = {}  # type: ignore[var-annotated]
    languages = {Language('spa')}

    with SubtitulamosProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)  # type: ignore[arg-type]
        assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_not_exist_series(caplog: pytest.LogCaptureFixture, episodes: dict[str, Episode]) -> None:
    with caplog.at_level(logging.DEBUG, logger=logger_name), SubtitulamosProvider() as provider:
        video = episodes['fake_show_s13e03']
        languages = {Language('spa')}

        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) == 0
        assert caplog.records[-1].message.endswith('Series not found')


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_not_exist_season(caplog: pytest.LogCaptureFixture, episodes: dict[str, Episode]) -> None:
    with caplog.at_level(logging.DEBUG, logger=logger_name), SubtitulamosProvider() as provider:
        video = episodes['bbt_s07e05']
        languages = {Language('eng'), Language('spa')}

        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) == 0
        assert caplog.records[-1].message.endswith('Season not found')


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_not_exist_episode(caplog: pytest.LogCaptureFixture, episodes: dict[str, Episode]) -> None:
    with caplog.at_level(logging.DEBUG, logger=logger_name), SubtitulamosProvider() as provider:
        video = episodes['fear_walking_dead_s03e10']
        languages = {Language('eng'), Language('spa')}

        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) == 0
        assert caplog.records[-1].message.endswith('Episode not found')


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_not_exist_language(caplog: pytest.LogCaptureFixture, episodes: dict[str, Episode]) -> None:
    with caplog.at_level(logging.DEBUG, logger=logger_name), SubtitulamosProvider() as provider:
        video = episodes['dw_s13e03']
        languages = {Language('spa', 'MX')}

        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_with_spanish_non_mx_search(
    caplog: pytest.LogCaptureFixture,
    episodes: dict[str, Episode],
) -> None:
    with caplog.at_level(logging.DEBUG, logger=logger_name), SubtitulamosProvider() as provider:
        video = episodes['bbt_s11e16']
        languages = {Language('spa', 'AR')}

        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) > 0
        assert all(s.language == Language('spa', 'AR') for s in subtitles)


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s11e16']
    languages = {Language('eng'), Language('spa')}
    with SubtitulamosProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) >= 1
        subtitle = subtitles[0]

        provider.download_subtitle(subtitle)
        assert subtitle.content is not None
        assert subtitle.is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_year(episodes: dict[str, Episode]) -> None:
    video = episodes['charmed_s01e01']
    languages = {Language('eng')}
    with SubtitulamosProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) >= 1
        subtitle = subtitles[0]

        provider.download_subtitle(subtitle)
        assert subtitle.content is not None
        assert subtitle.is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_last_season(episodes: dict[str, Episode]) -> None:
    video = episodes['dw_s13e03']
    languages = {Language('eng'), Language('spa')}
    with (
        SubtitulamosProvider() as provider,
        patch.object(SubtitulamosProvider, '_read_series', wraps=provider._read_series) as mock,
    ):
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) >= 1
        subtitle = subtitles[0]

        assert mock.call_count == 2
        assert mock.call_args_list[1].args[0] == '/episodes/8685/doctor-who-13x03-chapter-three-once-upon-time'

        provider.download_subtitle(subtitle)
        assert subtitle.content is not None
        assert subtitle.is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_first_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['charmed_s01e01']
    languages = {Language('eng')}
    with (
        SubtitulamosProvider() as provider,
        patch.object(SubtitulamosProvider, '_read_series', wraps=provider._read_series) as mock,
    ):
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) >= 1
        subtitle = subtitles[0]

        assert mock.call_count == 2
        assert mock.call_args_list[1].args[0] == '/episodes/3250/charmed-2018-1x01-pilot'

        provider.download_subtitle(subtitle)
        assert subtitle.content is not None
        assert subtitle.is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_foo(episodes: dict[str, Episode]) -> None:
    video = episodes['dw_s13e03']
    languages = {Language('eng'), Language('spa')}
    with SubtitulamosProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) >= 1
        subtitle = subtitles[0]

        provider.download_subtitle(subtitle)
        assert subtitle.content is not None
        assert subtitle.is_valid() is True


@pytest.mark.integration
def test_download_subtitle_missing_download_link() -> None:
    subtitle = SubtitulamosSubtitle(
        language=Language('spa'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=11,
        episode=16,
        title='the neonatal nomenclature',
        year=2007,
        release_group='AVS/SVA',
    )

    with SubtitulamosProvider() as provider:
        provider.download_subtitle(subtitle)
        assert subtitle.content is None
        assert subtitle.is_valid() is False


@pytest.mark.integration
def test_download_subtitle_without_initialization() -> None:
    subtitle = SubtitulamosSubtitle(
        language=Language('spa'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=11,
        episode=16,
        title='the neonatal nomenclature',
        year=2007,
        release_group='AVS/SVA',
    )

    provider = SubtitulamosProvider()
    with pytest.raises(NotInitializedProviderError):
        provider.download_subtitle(subtitle)
