import asyncio
import logging
import os
from contextlib import contextmanager
from functools import partial

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QImage, QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QFrame, QStyle

from fuocore.core.player import State as PlayerState
from fuocore.core.source import Source

from feeluown.config import config
from feeluown.components.history import HistoriesModel
from feeluown.components.library import LibrariesModel

from .consts import APP_ICON
from .hotkey import Hotkey
from .img_ctl import ImgController
from .player import Player
from .plugin import PluginsManager
from .request import Request
from .tips import TipsManager
from .ui import Ui
from .version import VersionManager

logger = logging.getLogger(__name__)


class AppCodeRunnerMixin(object):
    def exec_(self, code):
        obj = compile(code, '<string>', 'single')
        g = {
            'app': self,
            'player': self.player
        }
        exec(obj, g)


class App(QFrame, AppCodeRunnerMixin):

    initialized = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.player = Player()
        self.playlist = self.player.playlist
        self.request = Request(self)
        self.tips_manager = TipsManager(self)
        self.hotkey_manager = Hotkey(self)
        self.img_ctl = ImgController(self)
        self.plugins_manager = PluginsManager(self)
        self.version_manager = VersionManager(self)
        self.provider_manager = Source(prvs=set())
        # self.load_qss()

        self.histories = HistoriesModel(parent=self)
        self.libraries = LibrariesModel([], parent=self)

        self.ui = Ui(self)

        self._init_managers()

        self.player_pixmap = None

        self.resize(1000, 618)
        self.setObjectName('app')
        QApplication.setWindowIcon(QIcon(APP_ICON))

        self.bind_signal()
        self.initialize()

    def initialize(self):
        logger.debug('App start initializing...')
        self.initialized.emit()
        logger.debug('App start initializing...done')

    def scan_fuo_files(self):
        fuo_files = config.FUO_FILES
        f_list = []
        for filepath in fuo_files:
            if not os.path.exists(filepath):
                continue
            if os.path.isdir(filepath):
                for fname in os.listdir(filepath):
                    fpath = os.path.join(filepath, fname)
                    if os.path.isfile(fpath):
                        f_list.append(fpath)
            else:
                f_list.append(filepath)

        for fpath in f_list:
            basename = os.path.basename(fpath)
            if not basename.endswith('.fuo'):
                continue
            name = basename.rsplit('.', 1)[0]

    def bind_signal(self):
        top_panel = self.ui.top_panel

        self.player.state_changed.connect(self._on_player_status_changed)
        self.player.position_changed.connect(self._on_player_position_changed)
        self.player.duration_changed.connect(self._on_player_duration_changed)
        # FIXME:
        self.player.playlist.playback_mode_changed.connect(
            top_panel.pc_panel.on_playback_mode_changed)
        self.player.playlist.song_changed.connect(
            top_panel.pc_panel.on_player_song_changed)

        self.request.connected_signal.connect(self._on_network_connected)
        self.request.disconnected_signal.connect(self._on_network_disconnected)
        self.request.slow_signal.connect(self._on_network_slow)
        self.request.server_error_signal.connect(self._on_network_server_error)

        #top_panel.pc_panel.volume_slider.sliderMoved.connect(
        #    self.change_volume)

    def _init_managers(self):
        self.plugins_manager.scan()
        app_event_loop = asyncio.get_event_loop()
        app_event_loop.call_later(
            8, partial(asyncio.Task, self.version_manager.check_release()))
        self.tips_manager.show_random_tip()

    @contextmanager
    def action_log(self, s):
        self.ui.magicbox.show_msg(s + '...', timeout=-1)  # doing
        try:
            yield
        except Exception:
            self.ui.magicbox.show_msg(s + '...failed')  # failed
            raise
        else:
            self.ui.magicbox.show_msg(s + '...done')  # done

    def notify(self, text, error=False):
        pass

    def _on_player_position_changed(self, ms):
        self.ui.top_panel.pc_panel.on_position_changed(ms*1000)
        self.ui.top_panel.pc_panel.progress_slider.update_state(ms*1000)

    def _on_player_duration_changed(self, ms):
        self.ui.top_panel.pc_panel.on_duration_changed(ms*1000)
        self.ui.top_panel.pc_panel.progress_slider.set_duration(ms*1000)

    def _on_player_status_changed(self, state):
        pp_btn = self.ui.top_panel.pc_panel.pp_btn
        if state == PlayerState.playing:
            pp_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            pp_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def _on_network_slow(self):
        pass

    def _on_network_connected(self):
        pass

    def _on_network_server_error(self):
        pass

    def _on_network_disconnected(self):
        pass

    def change_volume(self, value):
        self.player.volume = value

    def pixmap_from_url(self, url, callback=None):
        # FIXME: only neteasemusic img url accept the params
        data = {'param': '{0}y{0}'.format(self.width())}
        res = self.request.get(url, data)
        if res is None:
            return None
        img = QImage()
        img.loadFromData(res.content)
        pixmap = QPixmap(img)
        if pixmap.isNull():
            return None
        if callback is not None:
            callback(pixmap)
        return pixmap

    def closeEvent(self, event):
        try:
            self.player.stop()
            self.player.shutdown()
        except Exception as e:
            pass
        QApplication.quit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
