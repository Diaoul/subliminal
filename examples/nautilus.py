# -*- coding: utf-8 -*-
from __future__ import division
from collections import defaultdict
from datetime import timedelta
import locale
from locale import gettext as _
import os

from babelfish import Language
from gi.repository import GObject, Gtk, Nautilus
from subliminal import (VIDEO_EXTENSIONS, ProviderPool, __copyright__, __version__, check_video, compute_score,
                        provider_manager, region, save_subtitles, scan_video, scan_videos)
from subliminal.cli import Config, MutexLock, app_dir, cache_file, config_file

locale.bindtextdomain('subliminal', os.path.join(os.path.dirname(__file__), 'subliminal', 'locale'))
locale.textdomain('subliminal')

ignored_languages = {Language(l) for l in (
    'ang', 'arc', 'dsb', 'dum', 'enm', 'frm', 'fro', 'gmh', 'goh', 'grc', 'ina', 'mga', 'mis', 'nds', 'non', 'ota',
    'peo', 'pro', 'sga', 'und'
)}


class ChooseHandler(object):
    """Signal handler for the choose window.

    This class will download the selected subtitle on row-activated signal.

    :param config: a configuration object.
    :type config: :class:`~subliminal.cli.Config`
    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param subtitles: the available of subtitles.
    :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`

    """
    def __init__(self, config, video, subtitles):
        self.config = config
        self.video = video
        self.subtitles = {s.provider_name + '-' + s.id: s for s in subtitles}

    def on_subtitles_treeview_row_activated(self, treeview, path, view_column):
        model = treeview.get_model()
        iter = model.get_iter(path)

        # return if already downloaded
        if model.get_value(iter, 6):
            return

        # get the subtitle object
        subtitle = self.subtitles[model.get_value(iter, 3).lower() + '-' + model.get_value(iter, 0)]

        # download the subtitle
        with ProviderPool(providers=self.config.providers, provider_configs=self.config.provider_configs) as pool:
            pool.download_subtitle(subtitle)

        # save the subtitle
        save_subtitles(self.video, [subtitle], single=self.config.single)

        # mark the subtitle as downloaded
        model.set_value(iter, 6, True)

    def on_subtitles_scrolledwindow_delete_event(self, *args):
        Gtk.main_quit(*args)


class ConfigHandler(object):
    """Signal handler for the configuration window.

    This class converts the values from the window and forward them to the configuration object. When the window is
    closed, the configuration is written.

    :param config: a configuration object.
    :type config: :class:`~subliminal.cli.Config`

    """
    def __init__(self, config):
        self.config = config

    def on_languages_treeview_selection_changed(self, selection):
        model, paths = selection.get_selected_rows()
        languages = {Language.fromietf(model.get_value(model.get_iter(p), 1)) for p in paths}
        if languages:
            self.config.languages = languages

    def on_providers_treeview_selection_changed(self, selection):
        model, paths = selection.get_selected_rows()
        providers = [model.get_value(model.get_iter(p), 0).lower() for p in paths]
        if providers:
            self.config.providers = providers

    def on_single_switch_active_notify(self, switch, gparam):
        self.config.single = switch.get_active()

    def on_embedded_subtitles_switch_active_notify(self, switch, gparam):
        self.config.embedded_subtitles = switch.get_active()

    def on_age_spinbutton_value_changed(self, spin_button):
        self.config.age = timedelta(days=spin_button.get_value())

    def on_hearing_impaired_switch_active_notify(self, switch, gparam):
        self.config.hearing_impaired = switch.get_active()

    def on_min_score_spinbutton_value_changed(self, spin_button):
        self.config.min_score = spin_button.get_value()

    def on_config_window_delete_event(self, *args):
        self.config.write()
        Gtk.main_quit(*args)


class SubliminalExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        # create app directory
        try:
            os.makedirs(app_dir)
        except OSError:
            if not os.path.isdir(app_dir):
                raise

        # open config file
        self.config = Config(os.path.join(app_dir, config_file))
        self.config.read()

        # configure cache
        region.configure('dogpile.cache.dbm', expiration_time=timedelta(days=30),
                         arguments={'filename': os.path.join(app_dir, cache_file), 'lock_factory': MutexLock})

    def get_file_items(self, window, files):
        # lightweight filter on file type and extension
        if not any(f.is_directory() or f.get_name().endswith(VIDEO_EXTENSIONS) for f in files):
            return

        # create subliminal menu
        subliminal_menuitem = Nautilus.MenuItem(name='SubliminalMenu::Subliminal', label='Subliminal')
        sub_menus = Nautilus.Menu()
        subliminal_menuitem.set_submenu(sub_menus)

        # create choose submenu on single file
        if len(files) == 1 and not files[0].is_directory():
            choose_menuitem = Nautilus.MenuItem(name='SubliminalSubMenu::Choose', label=_('Choose subtitles'))
            choose_menuitem.connect('activate', self.choose_callback, files)
            sub_menus.append_item(choose_menuitem)

        # create download submenu
        download_menuitem = Nautilus.MenuItem(name='SubliminalSubMenu::Download', label=_('Download subtitles'))
        download_menuitem.connect('activate', self.download_callback, files)
        sub_menus.append_item(download_menuitem)

        # create configure submenu
        configure_menuitem = Nautilus.MenuItem(name='SubliminalSubMenu::Configure', label=_('Configure...'))
        configure_menuitem.connect('activate', self.config_callback)
        sub_menus.append_item(configure_menuitem)

        return subliminal_menuitem,

    def get_background_items(self, window, current_folder):
        return []

    def choose_callback(self, menuitem, files):
        # scan and check the video
        video = scan_video(files[0].get_location().get_path(), subtitles=True,
                           embedded_subtitles=self.config.embedded_subtitles)
        if not check_video(video, languages=self.config.languages, undefined=self.config.single):
            return

        # list subtitles
        with ProviderPool(providers=self.config.providers, provider_configs=self.config.provider_configs) as pool:
            subtitles = pool.list_subtitles(video, self.config.languages)

        # load the interface
        builder = Gtk.Builder()
        builder.set_translation_domain('subliminal')
        builder.add_from_file(os.path.join(os.path.dirname(__file__), 'subliminal', 'ui', 'choose.glade'))

        # set the video filename
        video_filename = builder.get_object('video_filename_label')
        video_filename.set_text(files[0].get_name())

        # fill the subtitle liststore
        subtitle_liststore = builder.get_object('subtitle_liststore')
        for s in subtitles:
            matches = s.get_matches(video, hearing_impaired=self.config.hearing_impaired)
            scaled_score = compute_score(matches, video)
            if s.hearing_impaired == self.config.hearing_impaired:
                scaled_score -= video.scores['hearing_impaired']
            scaled_score *= 100 / video.scores['hash']
            subtitle_liststore.append([s.id, nice_language(s.language), scaled_score, s.provider_name.capitalize(),
                                       s.hearing_impaired, s.page_link, False])
        subtitle_liststore.set_sort_column_id(2, Gtk.SortType.DESCENDING)

        # connect signals
        builder.connect_signals(ChooseHandler(self.config, video, subtitles))

        # display window
        window = builder.get_object('subtitle_window')
        window.show_all()
        Gtk.main()

    def download_callback(self, menuitem, files):
        # scan videos
        videos = []
        for f in files:
            # ignore non-writable locations
            if not f.can_write():
                continue

            # directories
            if f.is_directory():
                try:
                    scanned_videos = scan_videos(f.get_location().get_path(), subtitles=True,
                                                 embedded_subtitles=self.config.embedded_subtitles)
                except:
                    continue
                for video in scanned_videos:
                    if check_video(video, languages=self.config.languages, age=self.config.age,
                                   undefined=self.config.single):
                        videos.append(video)
                continue

            # other inputs
            try:
                video = scan_video(f.get_location().get_path(), subtitles=True,
                                   embedded_subtitles=self.config.embedded_subtitles)
            except:
                continue
            if check_video(video, languages=self.config.languages, undefined=self.config.single):
                videos.append(video)

        # download best subtitles
        downloaded_subtitles = defaultdict(list)
        with ProviderPool(providers=self.config.providers, provider_configs=self.config.provider_configs) as pool:
            for v in videos:
                subtitles = pool.download_best_subtitles(
                    pool.list_subtitles(v, self.config.languages - v.subtitle_languages),
                    v, self.config.languages, min_score=v.scores['hash'] * self.config.min_score / 100,
                    hearing_impaired=self.config.hearing_impaired, only_one=self.config.single
                )
                downloaded_subtitles[v] = subtitles

        # save subtitles
        for v, subtitles in downloaded_subtitles.items():
            save_subtitles(v, subtitles, single=self.config.single)

    def config_callback(self, *args, **kwargs):
        # load the interface
        builder = Gtk.Builder()
        builder.set_translation_domain('subliminal')
        builder.add_from_file(os.path.join(os.path.dirname(__file__), 'subliminal', 'ui', 'config.glade'))

        # configure the about page
        aboutdialog = builder.get_object('aboutdialog')
        aboutdialog.set_version(__version__)
        aboutdialog.set_copyright(__copyright__)
        aboutdialog.vbox.reparent(builder.get_object('about_box'))

        # fill the language liststore
        available_languages = set()
        for provider in provider_manager:
            available_languages |= provider.plugin.languages
        language_liststore = builder.get_object('language_liststore')
        for language in sorted(available_languages - ignored_languages, key=nice_language):
            language_liststore.append([nice_language(language), str(language)])

        # set language selection
        language_treeselection = builder.get_object('language_treeselection')
        for language in language_liststore:
            if Language.fromietf(language[1]) in self.config.languages:
                language_treeselection.select_path(language.path)

        # fill the provider liststore
        provider_liststore = builder.get_object('provider_liststore')
        for provider in sorted([p.name for p in provider_manager]):
            provider_liststore.append([provider.capitalize(), str(self.config.provider_configs.get(provider, ''))])

        # set provider selection
        provider_treeselection = builder.get_object('provider_treeselection')
        for provider in provider_liststore:
            if provider[0].lower() in self.config.providers:
                provider_treeselection.select_iter(provider.iter)

        # set single state
        single_switch = builder.get_object('single_switch')
        single_switch.set_active(self.config.single)

        # set embedded subtitles state
        embedded_subtitles_switch = builder.get_object('embedded_subtitles_switch')
        embedded_subtitles_switch.set_active(self.config.embedded_subtitles)

        # set age value
        age_spinbutton = builder.get_object('age_spinbutton')
        age_spinbutton.set_value(self.config.age.days)

        # set hearing impaired state
        hearing_impaired_switch = builder.get_object('hearing_impaired_switch')
        hearing_impaired_switch.set_active(self.config.hearing_impaired)

        # set min score value
        min_score_spinbutton = builder.get_object('min_score_spinbutton')
        min_score_spinbutton.set_value(self.config.min_score)

        # connect signals
        builder.connect_signals(ConfigHandler(self.config))

        # display window
        window = builder.get_object('config_window')
        window.show_all()
        Gtk.main()


def nice_language(language):
    """Format a :class:`~babelfish.Language` in a nice string with country name if any.

    :param language: the language.
    :type language: :class:`~babelfish.Language`
    :return: a nice representation of the language.
    :rtype: str

    """
    if language.country is not None:
        return '{name} ({country})'.format(name=language.name, country=language.country.name.capitalize())
    return language.name
