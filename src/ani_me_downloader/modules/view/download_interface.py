from PyQt5.QtWidgets import (QLabel, QTreeWidget, QTreeWidgetItem, QProgressBar,
                             QSplitter, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QMenu, QAction, QComboBox, QStackedWidget, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices
from .base_interface import BaseInterface
from ..common.style_sheet import StyleSheet


class DownloadInterface(BaseInterface):
    pauseResumeSignal = pyqtSignal(str)
    openFolderSignal = pyqtSignal(str)
    deleteSignal = pyqtSignal(str, bool)
    changePrioritySignal = pyqtSignal(str, int, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("downloadInterface")
        
        # Main layout with splitter for torrent list and details
        self.splitter = QSplitter(Qt.Vertical, self)
        self.torrent_list = QTreeWidget()
        self.torrent_list.setIndentation(0)
        self.torrent_list.setObjectName("torrentList")
        self.torrent_list.setUniformRowHeights(True)
        self.torrent_list.setColumnCount(9)
        self.torrent_list.setHeaderLabels(["Name", "Size", "Progress", "Status", "Seeds", "Peers", "DL Speed", "UL Speed", "ETA"])
        self.torrent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.torrent_list.customContextMenuRequested.connect(self.show_context_menu)
        self.torrent_list.itemClicked.connect(self.on_item_clicked)
        self.torrent_list.setAlternatingRowColors(True)
        self.torrent_list.setSortingEnabled(True)
        self.splitter.addWidget(self.torrent_list)
        
        # Detail panel (initially collapsed)
        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("detailPanel")
        self.detail_panel.setMinimumHeight(200)  # Set minimum height
        self.panel_visible = True  # Track panel visibility
   
        detail_layout = QVBoxLayout(self.detail_panel)
        button_layout = QHBoxLayout()

        self.detail_button = QPushButton("Details")
        self.content_button = QPushButton("Content")
        self.detail_button.clicked.connect(lambda: self.show_panel("detail"))
        self.content_button.clicked.connect(lambda: self.show_panel("content"))
        self.toggle_panel_button = QPushButton("Hide Details")
        self.toggle_panel_button.clicked.connect(self.toggle_panel)
        button_layout.addStretch()  # Push toggle button to the right
        button_layout.addWidget(self.toggle_panel_button)
        button_layout.addWidget(self.detail_button)
        button_layout.addWidget(self.content_button)
        detail_layout.addLayout(button_layout)
        
        self.panel_stack = QStackedWidget()
        
        # detail_page with dynamic torrent details
        self.detail_page = QWidget()
        dp_layout = QVBoxLayout(self.detail_page)
        self.detail_label = QLabel("Select a torrent to see details.")
        self.detail_label.setWordWrap(True)
        self.detail_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        dp_layout.addWidget(self.detail_label)
        
        # content_page with file list (for single or multiple files)
        self.content_page = QWidget()
        cp_layout = QVBoxLayout(self.content_page)
        self.content_tree = QTreeWidget()
        self.content_tree.setIndentation(0)
        self.content_tree.setObjectName("contentTree")
        self.content_tree.setAlternatingRowColors(True)
        self.content_tree.setColumnCount(5)
        self.content_tree.setHeaderLabels(["Name", "Size", "Progress", "Priority", "Remaining"])
        cp_layout.addWidget(self.content_tree)
        
        self.panel_stack.addWidget(self.detail_page)
        self.panel_stack.addWidget(self.content_page)
        detail_layout.addWidget(self.panel_stack)
        self.detail_panel.setMaximumHeight(0)
        self.splitter.addWidget(self.detail_panel)
        
        self.vBoxLayout.addWidget(self.splitter)
        StyleSheet.DOWNLOAD_INTERFACE.apply(self)
        self.torrent_items = {}  # Track items by torrent name
        self.torrent_data = {}   # Map torrent name to real torrent objects
        self.current_torrent = None 
        self.resize_columns()

    def on_item_clicked(self, item, column):
        """Handle torrent item click to show details"""
        self.current_torrent = item.text(0)
        self.populate_detail_panel(item)

        # Make sure panel is visible when item is clicked
        if not self.panel_visible:
            self.toggle_panel()

        # Default to detail view on click
        self.show_panel("detail")

    def resizeEvent(self, event):
        """Update column sizes when the window is resized"""
        super().resizeEvent(event)
        self.resize_columns()

    def resize_columns(self):
        """Set optimal column sizes for both tree widgets"""
        # Main torrent list columns
        total_width = self.torrent_list.width()
        self.torrent_list.setColumnWidth(0, int(total_width * 0.35))  # Name (35%)
        self.torrent_list.setColumnWidth(1, int(total_width * 0.10))  # Size (8%)
        self.torrent_list.setColumnWidth(2, int(total_width * 0.15))  # Progress (15%)
        self.torrent_list.setColumnWidth(3, int(total_width * 0.12))  # Status (10%)
        self.torrent_list.setColumnWidth(4, int(total_width * 0.07))  # Seeds (5%)
        self.torrent_list.setColumnWidth(5, int(total_width * 0.07))  # Peers (5%)
        self.torrent_list.setColumnWidth(6, int(total_width * 0.11))  # DL Speed (8%)
        self.torrent_list.setColumnWidth(7, int(total_width * 0.11))  # UL Speed (7%)
        self.torrent_list.setColumnWidth(8, int(total_width * 0.07))  # ETA (7%)

        # Content tree columns
        content_width = self.content_tree.width()
        self.content_tree.setColumnWidth(0, int(content_width * 0.40))  # Name (40%)
        self.content_tree.setColumnWidth(1, int(content_width * 0.10))  # Size (10%)
        self.content_tree.setColumnWidth(2, int(content_width * 0.20))  # Progress (20%)
        self.content_tree.setColumnWidth(3, int(content_width * 0.15))  # Priority (15%)
        self.content_tree.setColumnWidth(4, int(content_width * 0.15))  # Remaining (15%)

    def toggle_panel(self):
        """Toggle the visibility of the detail panel"""
        if self.panel_visible:
            # Hide the panel
            current_sizes = self.splitter.sizes()
            self.splitter.setSizes([current_sizes[0] + current_sizes[1], 0])
            self.toggle_panel_button.setText("Show Details")
            self.panel_visible = False
        else:
            # Show the panel
            total_height = self.splitter.height()
            self.splitter.setSizes([int(total_height * 0.7), int(total_height * 0.3)])
            self.toggle_panel_button.setText("Hide Details")
            self.panel_visible = True

    def show_panel(self, panel_type):
        """Show detail or content panel and make sure splitter shows it"""
        # Make sure panel is visible
        if not self.panel_visible:
            self.toggle_panel()

        # Set the currently visible panel
        if panel_type == "detail":
            self.panel_stack.setCurrentWidget(self.detail_page)
            self.detail_button.setStyleSheet("background-color: #29f1ff;")
            self.content_button.setStyleSheet("")
        else:
            self.panel_stack.setCurrentWidget(self.content_page)
            self.content_button.setStyleSheet("background-color: #29f1ff;")
            self.detail_button.setStyleSheet("")

    def set_torrent_data(self, torrents):
        """Register the list of torrent objects so that file info can be displayed dynamically."""
        print(f"DownloadInterface: set_torrent_data called with {len(torrents)} torrents")
        self.torrent_data = {torrent.name: torrent for torrent in torrents}
    
        # Load any existing torrents to display
        for torrent in torrents:
            if torrent.name not in self.torrent_items:
                print(f"Adding torrent to UI: {torrent.name}")
                item = self.add_download(torrent.name)
            else:
                print(f"Torrent already in UI: {torrent.name}")
                item = self.torrent_items[torrent.name]
    
            # Update UI with existing torrent data
            self.update_progress(
                torrent.name, 
                torrent.progress, 
                torrent.status, 
                torrent.dl_speed, 
                torrent.ul_speed, 
                torrent.eta
            )
    
    def add_download(self, name):
        """Add a new download entry to the UI with a progress bar widget."""
        item = QTreeWidgetItem([name, "", "", "pending", "", "", "0", "0", "0"])
        self.torrent_list.addTopLevelItem(item)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        self.torrent_list.setItemWidget(item, 2, progress_bar)
        self.torrent_items[name] = item
        return item

    def update_progress(self, name, progress, status, dl_speed, ul_speed=0, eta=0):
        """Update the download progress bar for a torrent."""
        found = False
        for i in range(self.torrent_list.topLevelItemCount()):
            item = self.torrent_list.topLevelItem(i)
            if name == item.text(0):
                found = True
                # Update torrent data dictionary if available
                torrent = self.torrent_data.get(name)
                if torrent:
                    torrent.progress = progress
                    torrent.status = status
                    torrent.dl_speed = dl_speed
                    torrent.ul_speed = ul_speed
                    torrent.eta = eta

                # Update the UI
                progress_bar = self.torrent_list.itemWidget(item, 2)
                if progress_bar:
                    progress_bar.setValue(int(progress))
                    progress_bar.setFormat(f"{progress:.1f}%")
                item.setText(3, status)
                item.setText(6, f"{dl_speed:.1f}")  # DL Speed in KB/s
                item.setText(7, f"{ul_speed:.1f}")   # UL Speed in KB/s
                item.setText(8, self.format_eta(eta))

                # Update size and seeds/peers if available
                if torrent:
                    item.setText(1, torrent.size)
                    item.setText(4, str(torrent.seeds))
                    item.setText(5, str(torrent.peers))

                # If this is the currently selected torrent, update detail panel
                if self.current_torrent == name:
                    self.populate_detail_panel(item)
                break
            
        if not found:
            print(f"Warning: Torrent '{name}' not found in UI list, adding it now")
            self.add_download(name)
            # Call update_progress again to update the new item
            self.update_progress(name, progress, status, dl_speed, ul_speed, eta)

    def format_eta(self, seconds):
        """Convert seconds into a human-readable ETA."""
        if seconds <= 0:
            return "∞"
        elif seconds < 60:
            return f"{int(seconds)} sec"
        elif seconds < 3600:
            return f"{int(seconds/60)} min"
        else:
            hours = int(seconds/3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} hr {minutes} min"

    def show_context_menu(self, pos):
        item = self.torrent_list.itemAt(pos)
        if item:
            menu = QMenu()
            status = item.text(3).lower()
            
            # Create appropriate action based on torrent status
            if status == "paused":
                action1 = QAction("Resume", self)
            elif status == "seeding":
                action1 = QAction("Stop", self)
            else:
                action1 = QAction("Pause", self)
                
            action2 = QAction("Open Containing Folder", self)
            action3 = QAction("Delete", self)
            action4 = QAction("Delete with Files", self)
            
            menu.addAction(action1)
            menu.addAction(action2)
            menu.addSeparator()
            menu.addAction(action3)
            menu.addAction(action4)
            
            action1.triggered.connect(lambda: self.handle_action(action1.text(), item))
            action2.triggered.connect(lambda: self.handle_action("open", item))
            action3.triggered.connect(lambda: self.handle_action("delete", item))
            action4.triggered.connect(lambda: self.handle_action("delete_with_files", item))
            
            menu.exec_(self.torrent_list.viewport().mapToGlobal(pos))
            # Also update the detail panel on right-click
            self.populate_detail_panel(item)

    def handle_action(self, action, item):
        """Handle torrent action from context menu"""
        torrent_name = item.text(0)
        print(f"Action '{action}' on torrent '{torrent_name}'")
        
        if action.lower() in ["pause", "resume", "stop"]:
            self.pauseResumeSignal.emit(torrent_name)
        elif action.lower() == "open":
            torrent = self.torrent_data.get(torrent_name)
            if torrent and hasattr(torrent, 'path') and torrent.path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(torrent.path))
                
        elif action.lower() == "delete":
            self.deleteSignal.emit(torrent_name, False)  # False = don't delete files
        elif action.lower() == "delete_with_files":
            self.deleteSignal.emit(torrent_name, True)   # True = delete files too

    def on_item_clicked(self, item, column):
        self.current_torrent = item.text(0)
        self.populate_detail_panel(item)

    def populate_detail_panel(self, item):
        """Populate the detail and content panels based on the selected torrent item."""
        torrent_name = item.text(0)
        self.current_torrent = torrent_name

        # Update the detail panel with basic torrent info
        details = (
            f"Name: {item.text(0)}\nSize: {item.text(1)}\nStatus: {item.text(3)}\n"
            f"Seeds: {item.text(4)}\nPeers: {item.text(5)}\nDL Speed: {item.text(6)} KB/s\n"
            f"UL Speed: {item.text(7)} KB/s\nETA: {item.text(8)}"
        )
        self.detail_label.setText(details)

        # Update content panel with the real file list from the torrent data
        self.content_tree.clear()
        torrent_obj = self.torrent_data.get(torrent_name)

        if torrent_obj and hasattr(torrent_obj, "files") and torrent_obj.files:
            for index, f in enumerate(torrent_obj.files):
                file_item = QTreeWidgetItem([f["name"], f["size"], "", f["priority"], f["remaining"]])
                progress_bar = QProgressBar()
                progress_bar.setRange(0, 100)
                # Fix: Convert float to int for progress bar
                progress_bar.setValue(int(f["progress"]))
                progress_bar.setTextVisible(True)
                progress_bar.setFormat(f"{f['progress']:.1f}%")
                self.content_tree.addTopLevelItem(file_item)
                self.content_tree.setItemWidget(file_item, 2, progress_bar)

                # Add priority combo box
                prio_combo = QComboBox()
                prio_combo.addItems(["Skip","Low", "Normal", "High"])
                prio_combo.setCurrentText(f["priority"])

                # Use a lambda with default args to capture current values
                prio_combo.currentTextChanged.connect(
                    lambda value, idx=index, tname=torrent_name: 
                    self.changePrioritySignal.emit(tname, idx, value)
                )

                self.content_tree.setItemWidget(file_item, 3, prio_combo)
        else:
            # If no file data is available, show a message
            no_files_item = QTreeWidgetItem(["No files available or metadata not yet received"])
            self.content_tree.addTopLevelItem(no_files_item)

    def show_panel(self, panel_type):
        # Expand the detail panel to one-third of the window height
        self.detail_panel.setMaximumHeight(int(2*self.height() / 3))
        
        if panel_type == "detail":
            self.panel_stack.setCurrentWidget(self.detail_page)
            self.detail_button.setStyleSheet("background-color: #29f1ff;")
            self.content_button.setStyleSheet("")
        else:
            self.panel_stack.setCurrentWidget(self.content_page)
            self.content_button.setStyleSheet("background-color: #29f1ff;")
            self.detail_button.setStyleSheet("")

    def remove_torrent_from_ui(self, torrent_name):
        """Remove a torrent from the UI display"""
        # Find and remove the torrent item from the list
        for i in range(self.torrent_list.topLevelItemCount()):
            item = self.torrent_list.topLevelItem(i)
            if item.text(0) == torrent_name:
                # Remove from the tree widget
                self.torrent_list.takeTopLevelItem(i)
                
                # Remove from tracking dictionaries
                if torrent_name in self.torrent_items:
                    del self.torrent_items[torrent_name]
                if torrent_name in self.torrent_data:
                    del self.torrent_data[torrent_name]
                
                # Clear detail panel if this was the selected torrent
                if self.current_torrent == torrent_name:
                    self.current_torrent = None
                    self.detail_label.setText("Select a torrent to see details.")
                    self.content_tree.clear()
                
                print(f"Removed torrent '{torrent_name}' from UI")
                break