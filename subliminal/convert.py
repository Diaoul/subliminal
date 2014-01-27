# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import subprocess
import os
import logging
import babelfish
import enzyme
from .subtitle import get_subtitle_path

logger = logging.getLogger(__name__)

def scan_embedded_subtitle_languages(path):
    """Search for embedded subtitles from a video `path` and return their language

    :param string path: path to the video
    :return: found subtitle languages
    :rtype: set

    """
    dirpath, filename = os.path.split(path)
    subtitles = set()
    # enzyme
    try:
        if filename.endswith('.mkv'):
            with open(path, 'rb') as f:
                mkv = enzyme.MKV(f)
            if mkv.subtitle_tracks:
                # embedded subtitles
                for st in mkv.subtitle_tracks:
                    if st.language:
                        try:
                            subtitles.add(babelfish.Language.fromalpha3b(st.language))
                        except babelfish.Error:
                            logger.error('Embedded subtitle track language %r is not a valid language', st.language)
                            subtitles.add(babelfish.Language('und'))
                    elif st.name:
                        try:
                            subtitles.add(babelfish.Language.fromname(st.name))
                        except babelfish.Error:
                            logger.error('Embedded subtitle track name %r is not a valid language', st.name)
                            subtitles.add(babelfish.Language('und'))
                    else:
                        subtitles.add(babelfish.Language('und'))
                logger.debug('Found embedded subtitle %r with enzyme', subtitles)
            else:
                logger.debug('MKV has no subtitle track')
    except enzyme.Error:
        logger.error('Parsing video metadata with enzyme failed')
    return subtitles

def scan_available_subtitle_languages(path):
    """Search for '.srt' subtitles with alpha2 extension from a video `path` and return their language

    :param string path: path to the video
    :return: found subtitle languages
    :rtype: set

    """
    language_extensions = tuple('.' + c for c in babelfish.get_language_converter('alpha2').codes)
    dirpath, filename = os.path.split(path)
    subtitles = set()
    for p in os.listdir(dirpath):
        if isinstance(p, bytes) and p.startswith(os.path.splitext(filename)[0]) and p.endswith('.srt'):
            if os.path.splitext(p)[0].endswith(language_extensions):
                subtitles.add(babelfish.Language.fromalpha2(os.path.splitext(p)[0][-2:]))
            else:
                subtitles.add(babelfish.Language('und'))
    logger.debug('Found subtitles %r', subtitles)
    return subtitles
                
                
def convert_videos(videos, languages=None, language=babelfish.Language('eng'), subtitles_format='srt', video_format='mkv', video_savepath=None, single=True, delete_subtitles=False, force_copy=False):
    """Convert `videos` in .mkv using ffmpeg, including subtitles with the existing languages if not specified by `languages`.

    :param videos: videos to convert in .mkv
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages of subtitles to include in .mkv
    :type languages: set of :class:`babelfish.Language`
    :param str subtitles_format: subtitles format to be embedded in the video, only 'srt' is defined
    :param str video_format: format of the converted video, only 'mkv' is defined
    :param str video_savepath: path to save the output video. Same as input video if None.
    :param str loglevel: loglevel, default 'WARNING', set to 'DEBUG' to show strout from ffmpeg
    :param bool delete_subtitles: delete .srt file after conversion
    
    """
    converted_videos = set()
    if not language and single:
        logger.info('Language not specified, `und` chosen')
        language = babelfish.Language('und')
    if not languages and not single:
        if not language:
            logger.warning('At least one language must be selected')
            return convert_videos
        else:
            logger.info('%r selected', language)
            languages = {language}
    if not videos:
        logger.info('No video to convert')
        return converted_videos
    loglevel = logger.getEffectiveLevel()
    embedded_subtitles = set()
    for video in videos:
        try:
            dirpath, filename = os.path.split(video.name)
            Name, VideoExtension = os.path.splitext(filename)
            logger.debug('Video %r is being converted', filename)
            
            sformat = subtitles_format.strip('.')
            outformat = video_format.strip('.')
            #lang = language.alpha3
            
            # define path for the output video and check if the output video already exists
            if video_savepath:
                outpath = video_savepath
            else:
                outpath = dirpath
            outvid_apath = os.path.join(outpath, Name + '.' + outformat)
            if os.path.isfile(outvid_apath) and (not force_copy):
                # check if .mkv contains the subtitles for these languages   
                embedded_subtitles = scan_embedded_subtitle_languages(outvid_apath)
                # avoid video if it has already been encoded with the wanted subtitles
                if  languages <= embedded_subtitles:
                    logger.debug('Video %r already converted', video)
                    continue

            # check which subtitles are available to embed in the video
            available_subtitles = scan_available_subtitle_languages(video.name)
            
            # define the subtitles to be embedded
            embeddable_subtitles = languages.difference(embedded_subtitles) & available_subtitles
            logger.info('Subtitles to be embedded: %r', embeddable_subtitles)

            # for one single subtitle to embed, ffmpeg is used
            if single or len(embeddable_subtitles)==1:
                if not single:
                    lang = embeddable_subtitles.pop()
                else:
                    lang = language
                logger.debug('One subtitle to embed, language %r', lang.alpha3)
                insub_apath = get_subtitle_path(video.name, language=None if single else lang.alpha2)
                if not os.path.isfile(insub_apath):
                    logger.debug('Subtitle does not exist : %s', insub_apath)
                    continue
                
                # define command to ffmpeg to convert to .mkv and embed subtitle
                command = ["-i", video.name, "-i", insub_apath, "-c", "copy", "-metadata:s:s:0", "language=%s"%(lang.alpha3), outvid_apath]

                if loglevel >= 20:
                    command = ["ffmpeg", "-loglevel", "panic"] + command
                else:
                    command = ["ffmpeg"] + command
                
                Proc = subprocess.Popen(command)
                logger.info('Converting video %s ------', filename)
                Proc.wait()
                logger.info('---- Conversion finished.')
                converted_videos.add(video.name)

                # delete subtitle .srt files after conversion
                if delete_subtitles:
                    try:
                        os.remove(insub_apath)
                        logger.info('Subtitle file removed: %s', os.path.split(insub_apath)[1])
                    except OSError as e: # name the Exception `e`
                        logger.info("Failed with: %r", e.strerror) 
                        logger.info("Error code: %r", e.code) 
            
            # for multiple subtitles, mkvmerge is used
            elif not single and len(embeddable_subtitles)>=2:
                command = []
                if loglevel >= 30:
                    command = ['-q']
                elif loglevel == 10:
                    command = ['-v']
                  
                command = ['mkvmerge'] + command +['-o', outvid_apath, video.name]
                for lang in embeddable_subtitles:
                    logger.debug('... embed %r subtitle', lang.alpha3)

                    # check if subtitle exists
                    insub_apath = get_subtitle_path(video.name, language=lang)
                    #insub_apath = os.path.join(dirpath, Name + '.' + sformat)
                    if not os.path.isfile(insub_apath):
                        logger.debug('Subtitle does not exist : %s', insub_apath)
                        continue
                    
                    # define command to mkvmerge to embed the subtitle with `lang` language
                    command += ['--language', '0:%s'%(lang.alpha3), insub_apath] 

                    
                Proc = subprocess.Popen(command)
                logger.info('Converting video %s ------', filename)
                Proc.wait()
                logger.info('---- Conversion finished.')
                converted_videos.add(video.name)
                    
                # delete subtitle .srt files after conversion
                if delete_subtitles:
                    for lang in embeddable_subtitles:

                        insub_apath = get_subtitle_path(video.name, language=lang.alpha2)
                        
                        # check if subtitle exists
                        insub_apath = get_subtitle_path(video.name, language=lang.alpha2)
                        #insub_apath = os.path.join(dirpath, Name + '.' + sformat)
                        if not os.path.isfile(insub_apath):
                            logger.debug('Subtitle does not exist : %s', insub_apath)
                            continue
                        try:
                            os.remove(insub_apath)
                            logger.info('Subtitle file removed: %s', os.path.split(insub_apath)[1])
                        except OSError as e: # name the Exception `e`
                            logger.info("Failed with: %r", e.strerror) 
                            logger.info("Error code: %r", e.code) 
            else:
                logger.debug('No subtitles to embed')
        except Exception as e: # name the Exception `e`
            logger.info("Failed to convert video %r : %r", video, e) 
            # continue to next video if error occured in one video
            continue 
    return converted_videos
