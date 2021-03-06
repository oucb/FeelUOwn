from PyQt5.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QSize,
    Qt,
    QVariant,
)
from PyQt5.QtWidgets import (
    QListView,
    QSizePolicy,
)


class LibraryModel(object):
    # XXX: 把这个 Model 放到 fuocore 中去实现？
    # 这个东西有点像 fuocore 中的 provider
    def __init__(self, identifier, name, load_cb, icon=None, user=None,
                 **kwargs):
        self.identifier = identifier
        self.name = name
        self.load_cb = load_cb
        self.icon = icon or '♬ '
        self.user = user


class LibrariesModel(QAbstractListModel):
    def __init__(self, libraries=None, parent=None):
        super().__init__(parent)
        self._libraries = libraries or []

    def append(self, library):
        self._libraries.append(library)

    def rowCount(self, parent=QModelIndex()):
        return len(self._libraries)

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        row = index.row()
        if row >= len(self._libraries) or row < 0:
            return QVariant()

        library = self._libraries[row]
        if role == Qt.DisplayRole:
            return library.icon + ' ' + library.name
        elif role == Qt.UserRole:
            return library
        return QVariant()


class LibrariesView(QListView):
    def __init__(self, parent):
        super().__init__(parent)

        self.setMinimumHeight(100)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.clicked.connect(self._on_clicked)

    def _on_clicked(self, index):
        library = index.data(role=Qt.UserRole)
        library.load_cb()

    def sizeHint(self):
        height = 10
        if self.model().rowCount() > 0:
            height = self.model().rowCount() * self.sizeHintForRow(0)
        return QSize(self.width(), height)
