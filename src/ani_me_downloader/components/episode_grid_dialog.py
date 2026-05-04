# coding: utf-8
"""Per-episode status grid. Cells derived from `last_aired_episode` + records.
Click cycles TRACK_ONLY → QUEUED (= remove record) → DONE → TRACK_ONLY."""
from dataclasses import dataclass

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets.components.dialog_box.dialog import MaskDialogBase, Ui_MessageBox

from ..core.anime import Anime, DownloadMode, EpState, EpStatus
from ..view.style_sheet import StyleSheet


_KEY_TRACK_ONLY = "track_only"
_KEY_QUEUED = "queued"
_KEY_NOT_AIRED = "not_aired"
_KEY_DOWNLOADING = "downloading"
_KEY_DONE = "done"
_KEY_BATCHED = "batch"
_KEY_EXCLUDED = "excluded"  # outside ep_from..ep_to range


_STATUS_LABELS = {
    _KEY_TRACK_ONLY: "Track only",
    _KEY_QUEUED: "Queued",
    _KEY_DOWNLOADING: "Downloading",
    _KEY_DONE: "Done",
    _KEY_NOT_AIRED: "Not aired",
    _KEY_BATCHED: "Batched",
    _KEY_EXCLUDED: "Outside range",
}

_LEGEND = [
    (_KEY_TRACK_ONLY, "Track only"),
    (_KEY_QUEUED, "Queued"),
    (_KEY_DOWNLOADING, "Downloading"),
    (_KEY_DONE, "Done"),
    (_KEY_NOT_AIRED, "Not aired"),
    (_KEY_BATCHED, "Batched"),
    (_KEY_EXCLUDED, "Excluded"),
]

_AUTO_LOCKED_KEYS = {_KEY_NOT_AIRED, _KEY_DOWNLOADING, _KEY_BATCHED, _KEY_EXCLUDED}

# Hard cap on rendered cells. Shows like One Piece declare 2000+ episodes;
# a flat QGridLayout with that many widgets is laggy and offers no value
# for the user since they only need to see what's interesting (recently aired
# + records). Cap and surface a hint.
_MAX_RENDERED_CELLS = 600


def _record_key(rec: EpState) -> str:
    if rec.status is EpStatus.TRACK_ONLY:
        return _KEY_TRACK_ONLY
    if rec.status is EpStatus.DOWNLOADING:
        return _KEY_DOWNLOADING
    if rec.status is EpStatus.DONE:
        return _KEY_DONE
    if rec.status in (EpStatus.BATCH_PENDING, EpStatus.BATCH_DONE):
        return _KEY_BATCHED
    return _KEY_QUEUED


@dataclass
class _Cell:
    ep: int
    key: str
    record: EpState | None       # None = derived (no persisted record)
    locked: bool = False         # excluded-by-range cells lock to prevent meaningless edits


def _build_cells(anime: Anime) -> list[_Cell]:
    """Derive one cell per ep in 1..total_episodes. EPISODES mode honors
    ep_from/ep_to (out-of-range = locked track_only). TRACK_ONLY mode shows
    whatever the records say. BATCH mode never reaches here (rendered as message).

    For ongoing shows where total_episodes is unknown/zero, falls back to
    last_aired_episode + a small lookahead so the grid is never empty."""
    by_ep = {e.ep: e for e in anime.episodes if e.ep > 0}
    aired_cap = anime.last_aired_episode
    declared_total = anime.total_episodes
    # Defensive: if total is missing/zero, derive a reasonable upper bound
    # so the grid still shows something useful.
    effective_total = declared_total or max(aired_cap, max(by_ep, default=0))
    upper = anime.ep_to or effective_total or 1
    lower = max(1, anime.ep_from)
    is_episodes = anime.download_mode is DownloadMode.EPISODES
    cells: list[_Cell] = []
    for n in range(1, max(1, effective_total) + 1):
        rec = by_ep.get(n)
        if rec is not None:
            cells.append(_Cell(n, _record_key(rec), rec))
            continue
        if is_episodes and (n < lower or n > upper):
            cells.append(_Cell(n, _KEY_EXCLUDED, None, locked=True))
            continue
        if n > aired_cap:
            cells.append(_Cell(n, _KEY_NOT_AIRED, None))
        else:
            cells.append(_Cell(n, _KEY_QUEUED, None))
    return cells


def _is_locked(cell: _Cell) -> bool:
    return cell.locked or cell.key in _AUTO_LOCKED_KEYS


def _repolish(w: QWidget) -> None:
    s = w.style()
    s.unpolish(w)
    s.polish(w)
    w.update()


class _EpisodeCell(QLabel):
    def __init__(self, cell: _Cell, on_click, parent=None):
        super().__init__(parent)
        self.cell = cell
        self._on_click = on_click
        self.setObjectName("epCell")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(48)
        self.setMinimumWidth(60)
        self.refresh()

    def refresh(self):
        self.setText(f"Ep {self.cell.ep}")
        tip = _STATUS_LABELS.get(self.cell.key, self.cell.key)
        if self.cell.key == _KEY_EXCLUDED:
            tip = "Outside selected episode range"
        self.setToolTip(tip)
        self.setProperty("epStatus", self.cell.key)
        self.setCursor(
            Qt.ArrowCursor if _is_locked(self.cell) else Qt.PointingHandCursor
        )
        _repolish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not _is_locked(self.cell):
            self._on_click(self)
        super().mousePressEvent(event)


class EpisodeGridDialog(MaskDialogBase, Ui_MessageBox):
    """Grid of all episodes with cyclable per-episode status."""

    def __init__(self, anime: Anime, parent=None, coordinator=None):
        super().__init__(parent)
        self._setUpUi(f"Episodes — {anime.name}", "", self.widget)
        self.cancelButton.hide()
        self.yesButton.setText("Close")
        if hasattr(self, "contentLabel") and self.contentLabel is not None:
            self.contentLabel.hide()

        self.anime = anime
        self.coordinator = coordinator

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignCenter)
        self.textLayout.setContentsMargins(24, 20, 24, 8)

        body = QVBoxLayout()
        body.setContentsMargins(24, 0, 24, 8)
        body.setSpacing(10)
        self.vBoxLayout.insertLayout(1, body)

        if anime.download_mode is DownloadMode.BATCH:
            self._build_batch_placeholder(body)
            StyleSheet.EPISODE_GRID_DIALOG.apply(self.widget)
            return

        body.addLayout(self._build_legend())

        sep = QFrame()
        sep.setObjectName("epSeparator")
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        body.addWidget(sep)

        self._cols = 4 if anime.total_episodes < 15 else 5
        self._cells: list[_EpisodeCell] = []

        scroll = QScrollArea()
        scroll.setObjectName("epScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(self._cols * 110)
        scroll.setMinimumHeight(360)
        scroll.setMaximumHeight(520)
        scroll.setFrameShape(QFrame.NoFrame)

        grid_host = QWidget()
        grid_host.setObjectName("epGridHost")
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        all_cells = _build_cells(anime)
        if not all_cells:
            empty = QLabel("Nothing to show — no episode data yet.")
            empty.setObjectName("epEmpty")
            empty.setAlignment(Qt.AlignCenter)
            grid.addWidget(empty, 0, 0)
        else:
            visible = self._slice_for_display(all_cells)
            for idx, cell_data in enumerate(visible):
                cell = _EpisodeCell(cell_data, self._on_cell_click)
                self._cells.append(cell)
                grid.addWidget(cell, idx // self._cols, idx % self._cols)
            if len(visible) < len(all_cells):
                first, last = visible[0].ep, visible[-1].ep
                hint = QLabel(
                    f"Showing eps {first}–{last} of {len(all_cells)}. "
                    "Long-running show: edit JSON for older eps."
                )
                hint.setObjectName("epEmpty")
                hint.setAlignment(Qt.AlignCenter)
                body.addWidget(hint)

        scroll.setWidget(grid_host)
        body.addWidget(scroll)

        StyleSheet.EPISODE_GRID_DIALOG.apply(self.widget)

    def _slice_for_display(self, cells: list[_Cell]) -> list[_Cell]:
        """Cap rendered cells. Centers window on `last_aired_episode` so the
        recent (most relevant) episodes are visible."""
        if len(cells) <= _MAX_RENDERED_CELLS:
            return cells
        focus = self.anime.last_aired_episode or len(cells)
        # find index of the focus ep (cells are 1-indexed by ep, in order)
        focus_idx = max(0, min(len(cells) - 1, focus - cells[0].ep))
        half = _MAX_RENDERED_CELLS // 2
        start = max(0, focus_idx - half)
        end = min(len(cells), start + _MAX_RENDERED_CELLS)
        start = max(0, end - _MAX_RENDERED_CELLS)
        return cells[start:end]

    def _build_batch_placeholder(self, body: QVBoxLayout) -> None:
        rec = next((e for e in self.anime.episodes if e.ep == 0), None)
        if rec is None:
            label = "Batch download — no torrent attached yet."
        elif rec.status is EpStatus.BATCH_DONE:
            label = "Batch download complete."
        else:
            label = "Batch download in progress."
        msg = QLabel(label)
        msg.setObjectName("epEmpty")
        msg.setAlignment(Qt.AlignCenter)
        body.addWidget(msg)

    def _build_legend(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 0, 0, 0)
        seen = set()
        for key, text in _LEGEND:
            if text in seen:
                continue
            seen.add(text)
            swatch = QLabel()
            swatch.setObjectName("epLegendSwatch")
            swatch.setAttribute(Qt.WA_StyledBackground, True)
            swatch.setProperty("epStatus", key)
            label = QLabel(text)
            label.setObjectName("epLegendText")
            wrap = QWidget()
            item = QHBoxLayout(wrap)
            item.setContentsMargins(0, 0, 0, 0)
            item.setSpacing(6)
            item.addWidget(swatch)
            item.addWidget(label)
            row.addWidget(wrap)
        row.addStretch()
        return row

    def _on_cell_click(self, widget: _EpisodeCell):
        cell = widget.cell
        prev = cell.key
        if prev == _KEY_TRACK_ONLY:
            # Remove record (if any) → derived. QUEUED if aired, NOT_AIRED otherwise.
            self.anime.episodes = [e for e in self.anime.episodes if e.ep != cell.ep]
            cell.record = None
            cell.key = (
                _KEY_QUEUED if cell.ep <= self.anime.last_aired_episode else _KEY_NOT_AIRED
            )
        elif prev == _KEY_QUEUED:
            rec = EpState(ep=cell.ep, status=EpStatus.DONE, magnet=None)
            self.anime.episodes.append(rec)
            cell.record = rec
            cell.key = _KEY_DONE
        elif prev == _KEY_DONE:
            if cell.record is None:
                # Defensive: shouldn't happen — DONE always has a record after the QUEUED→DONE transition above.
                return
            cell.record.status = EpStatus.TRACK_ONLY
            cell.record.magnet = None
            cell.key = _KEY_TRACK_ONLY
        else:
            return
        widget.refresh()
        self._persist()

    def _persist(self):
        if self.coordinator is None:
            return
        try:
            self.coordinator.state.save_animes()
            self.coordinator.animes_changed.emit()
        except Exception:
            pass

    def eventFilter(self, obj, e: QEvent):
        if obj is self.window() and e.type() == QEvent.Resize:
            self._adjustText()
        return super().eventFilter(obj, e)
