from babelfish import Language  # type: ignore[import-untyped]
from subliminal.core import scan_video
from subliminal.refiners.metadata import refine
from subliminal.video import Movie


def test_refine_video_metadata(mkv):
    scanned_video = scan_video(mkv['test5'])
    refine(scanned_video, embedded_subtitles=True)

    assert type(scanned_video) is Movie
    assert scanned_video.name == mkv['test5']
    assert scanned_video.source is None
    assert scanned_video.release_group is None
    assert scanned_video.resolution is None
    assert scanned_video.video_codec == 'H.264'
    assert scanned_video.audio_codec == 'AAC'
    assert scanned_video.imdb_id is None
    assert scanned_video.size == 31762747
    assert scanned_video.subtitle_languages == {
        Language('eng'),
        Language('spa'),
        Language('deu'),
        Language('jpn'),
        Language('und'),
        Language('ita'),
        Language('fra'),
        Language('hun'),
    }
    assert scanned_video.title == 'test5'
    assert scanned_video.year is None
