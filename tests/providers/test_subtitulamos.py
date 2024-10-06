import os

import pytest
from babelfish import Language, language_converters  # type: ignore[import-untyped]
from subliminal.providers.subtitulamos import SubtitulamosProvider
from vcr import VCR  # type: ignore[import-untyped]

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'subtitulamos')),
)


@pytest.mark.integration()
@vcr.use_cassette
def test_login():
    provider = SubtitulamosProvider()
    assert provider.session is None
    provider.initialize()
    assert provider.session is not None


@pytest.mark.integration()
@vcr.use_cassette
def test_logout():
    provider = SubtitulamosProvider()
    provider.initialize()
    provider.terminate()
    assert provider.session is None


@pytest.mark.integration()
@vcr.use_cassette
def test_download_subtitle(episodes):
    video = episodes['bbt_s11e16']
    languages = {Language('eng'), Language('spa')}
    with SubtitulamosProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) >= 1
        subtitle = subtitles[0]

        provider.download_subtitle(subtitle)
        assert subtitle.content is not None
        assert subtitle.is_valid() is True


@pytest.mark.converter()
def test_converter_convert_alpha3():
    assert language_converters['subtitulamos'].convert('cat') == 'Català'


@pytest.mark.converter()
def test_converter_convert_alpha3_country():
    assert language_converters['subtitulamos'].convert('spa', 'MX') == 'Español (Latinoamérica)'
    assert language_converters['subtitulamos'].convert('por', 'BR') == 'Brazilian'


@pytest.mark.converter()
def test_converter_convert_alpha3_name_converter():
    assert (
        language_converters['subtitulamos'].convert(
            'fra',
        )
        == 'French'
    )


@pytest.mark.converter()
def test_converter_reverse():
    assert language_converters['subtitulamos'].reverse('Español') == ('spa',)


@pytest.mark.converter()
def test_converter_reverse_country():
    assert language_converters['subtitulamos'].reverse('Español (España)') == ('spa',)
    assert language_converters['subtitulamos'].reverse('Español (Latinoamérica)') == ('spa', 'MX')


@pytest.mark.converter()
def test_converter_reverse_name_converter():
    assert language_converters['subtitulamos'].reverse('French') == ('fra', None, None)
