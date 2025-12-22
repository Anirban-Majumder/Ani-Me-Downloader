from PyQt5.QtCore import QThread, pyqtSignal
from ..common.utils import Constants, check_network
import sys
import os

# Debug: Print system info for troubleshooting native library issues
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print(f"Executable: {sys.executable}")

try:
    import libtorrent as lt
    print(f"libtorrent version: {lt.__version__}")
except ImportError as e:
    print(f"Failed to import libtorrent: {e}")
    # On Windows, check for missing DLLs
    if sys.platform == 'win32':
        print("Checking for Visual C++ Runtime...")
        import ctypes
        try:
            ctypes.CDLL("vcruntime140.dll")
            print("vcruntime140.dll: Found")
        except OSError:
            print("vcruntime140.dll: MISSING - Install Visual C++ Redistributable")
    lt = None
except Exception as e:
    print(f"Error loading libtorrent: {type(e).__name__}: {e}")
    lt = None

import time, math
from ..common.config import cfg


class RunThread(QThread):
    runSignal = pyqtSignal()
    def __init__(self):
        super().__init__()

    def run(self):
        import time
        while True:
            time.sleep(cfg.checkEpisodeInterval.value)
            self.runSignal.emit()


class AnimeThread(QThread):
    sendError = pyqtSignal(str)
    sendInfo = pyqtSignal(str)
    sendFinished = pyqtSignal(list)

    def __init__(self, animes):
        super().__init__()
        self.animes = animes

    def run(self):
        if not check_network():
            self.sendError.emit("There is something wrong with your Internet connection.")
            return

        for anime in self.animes:
            anime.start()
        self.sendFinished.emit(self.animes)
        self.sendInfo.emit("To see more details, please click the 'Library' button")


def save_resume_to_file(torrent_obj, resume_data):
    filename = os.path.join(torrent_obj.path, f".{torrent_obj.name}.fastresume")
    with open(filename, "wb") as f:
        f.write(resume_data)
    print(f"Saved resume data to {filename}")

def load_resume_from_file(torrent_obj):
    filename = os.path.join(torrent_obj.path, f".{torrent_obj.name}.fastresume")
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            return f.read()
    return None

def delete_resume_file(torrent_obj):
    filename = os.path.join(torrent_obj.path, f".{torrent_obj.name}.fastresume")
    if os.path.exists(filename):
        os.remove(filename)

class TorrentThread(QThread):
    progressSignal = pyqtSignal(str, float, str, float, float, int)
    exitSignal = pyqtSignal(list)
    torrentComplete = pyqtSignal(list)
    errorSignal = pyqtSignal(str)
    filesUpdatedSignal = pyqtSignal(str)  # Signal to notify when files are updated for a torrent

    def __init__(self, torrents):
        super().__init__()
        self.max_concurrent_downloads = cfg.maxConcurrentDownloads.value
        self.torrents = torrents
        self._session = None
        self._handles = {}  # Map torrent name to (torrent_obj, handle)
        self._stop = False
        self._paused_torrents = set()  # Keep track of which torrents are paused
        self._stalled_torrents = set()  # Keep track of which torrents are stalled due to concurrency limits
        self._active_downloads = 0  # Track how many torrents are actively downloading
        print("TorrentThread initialized.")

    def stop(self):
        self._stop = True

    def pause_torrent(self, torrent_name):
        """Pause a specific torrent by name"""
        if torrent_name in self._handles:
            torrent_obj, handle = self._handles[torrent_name]
            try:
                if torrent_obj.status not in ["paused", "completed"]:
                    handle.pause()
                    # Update status based on previous state
                    if torrent_obj.status == "seeding":
                        torrent_obj.status = "completed"
                    else:
                        torrent_obj.status = "paused"
                    
                    self._paused_torrents.add(torrent_name)
                    
                    # Decrease active download count if this was downloading
                    if torrent_obj.status in ["downloading", "stalled"]:
                        self._active_downloads = max(0, self._active_downloads - 1)
                        # Remove from stalled set if it was there
                        self._stalled_torrents.discard(torrent_name)
                        # Check if we can start any stalled torrents
                        self._manage_download_queue()
                    
                    print(f"Paused torrent: {torrent_name}")
                    return True
            except Exception as e:
                print(f"Error pausing torrent {torrent_name}: {e}")
        return False

    def resume_torrent(self, torrent_name):
        """Resume a specific torrent by name"""
        if torrent_name in self._handles:
            torrent_obj, handle = self._handles[torrent_name]
            try:
                if torrent_obj.status == "paused":
                    # Check if we have room for another active download
                    if torrent_obj.progress < 99.9 and self._active_downloads >= self.max_concurrent_downloads:
                        # Mark as stalled instead of starting it
                        torrent_obj.status = "stalled"
                        self._paused_torrents.discard(torrent_name)
                        self._stalled_torrents.add(torrent_name)
                        print(f"Torrent {torrent_name} moved to stalled (concurrency limit)")
                        return True
                    
                    handle.resume()
                    # Determine proper status based on progress
                    if torrent_obj.progress >= 99.9:
                        torrent_obj.status = "seeding"
                    else:
                        torrent_obj.status = "downloading"
                        self._active_downloads += 1
                    
                    self._paused_torrents.discard(torrent_name)
                    self._stalled_torrents.discard(torrent_name)
                    print(f"Resumed torrent: {torrent_name}")
                    return True
            except Exception as e:
                print(f"Error resuming torrent {torrent_name}: {e}")
        return False
    
    def _manage_download_queue(self):
        """Manage the download queue based on concurrency limits"""
        # If we have room for more active downloads, start some stalled torrents
        while self._active_downloads < self.max_concurrent_downloads and self._stalled_torrents:
            # Get a torrent from the stalled set
            torrent_name = next(iter(self._stalled_torrents))
            if torrent_name in self._handles:
                torrent_obj, handle = self._handles[torrent_name]
                handle.resume()
                torrent_obj.status = "downloading"
                self._stalled_torrents.remove(torrent_name)
                self._active_downloads += 1
                print(f"Started previously stalled torrent: {torrent_name}")

    def remove_torrent(self, torrent_name, delete_files=False):
        """Remove a torrent and optionally its files"""
        if torrent_name in self._handles:
            torrent_obj, handle = self._handles[torrent_name]
            try:
                # Save resume data if available
                if not handle.is_valid():
                    print(f"Handle for {torrent_name} is not valid, skipping resume data")
                else:
                    # Request resume data asynchronously
                    handle.save_resume_data()
                    print(f"Requested resume data for {torrent_name}")
                
                # Remove the torrent from the session
                self._session.remove_torrent(handle, int(delete_files))
                print(f"Removed torrent {torrent_name}, delete_files={delete_files}")
                
                # If this was downloading, decrease active count
                if torrent_obj.status == "downloading":
                    self._active_downloads = max(0, self._active_downloads - 1)
                
                # Remove from our tracking
                del self._handles[torrent_name]
                if torrent_name in self._paused_torrents:
                    self._paused_torrents.remove(torrent_name)
                if torrent_name in self._stalled_torrents:
                    self._stalled_torrents.remove(torrent_name)
                
                #delete resume data
                resume_file = os.path.join(torrent_obj.path, f".{torrent_obj.name}.fastresume")
                if os.path.exists(resume_file):
                    os.remove(resume_file)

                # Remove from torrents list
                for i, t in enumerate(self.torrents):
                    if t.name == torrent_name:
                        self.torrents.pop(i)
                        break

                
                
                # Check if we can start any stalled torrents
                self._manage_download_queue()
                
                return True
            except Exception as e:
                print(f"Error removing torrent: {e}")
                return False
        return False

    def set_file_priorities(self, torrent_name, file_index, priority):
        """Set priority for a specific file in a torrent"""
        if torrent_name in self._handles:
            torrent_obj, handle = self._handles[torrent_name]
            
            # Convert user-friendly priority to libtorrent priority
            lt_priority = {
                "High": 7,
                "Normal": 4,
                "Low": 1,
                "Skip": 0
            }.get(priority, 4)
            
            try:
                # Create a list of current priorities and update just the one we want
                if hasattr(handle, 'file_priorities') and callable(handle.file_priorities):
                    priorities = list(handle.file_priorities())
                    if 0 <= file_index < len(priorities):
                        priorities[file_index] = lt_priority
                        handle.prioritize_files(priorities)
                        
                        # Update our internal file info
                        if file_index < len(torrent_obj.files):
                            torrent_obj.files[file_index]["priority"] = priority
                        
                        print(f"Set priority for {torrent_name}, file {file_index} to {priority}")
                        return True
            except Exception as e:
                print(f"Error setting file priority: {e}")
        return False

    def _format_size(self, size_bytes):
        """Convert bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def _update_torrent_files(self, torrent_obj, handle):
        """Update the files list for a torrent"""
        try:
            # Modern way to check for metadata
            info = None
            try:
                info = handle.torrent_file()
            except:
                return False

            if not info:
                return False

            # Get torrent info - already have it from above
            file_storage = info.files()

            # Clear existing files
            torrent_obj.files = []

            # Get file priorities - modern approach
            priorities = []
            try:
                # For libtorrent 2.0+
                priorities = handle.get_file_priorities()
            except:
                # Fallback
                try:
                    priorities = handle.file_priorities()
                except:
                    priorities = [4] * file_storage.num_files()  # Normal priority default

            # Get file progress - modern approach
            file_progress = []
            try:
                file_progress = handle.file_progress()
            except:
                # Fallback to zeros if method not available
                file_progress = [0] * file_storage.num_files()

            # Map libtorrent priority values to our friendly names
            priority_map = {
                0: "Skip",
                1: "Low",
                4: "Normal", 
                7: "High"
            }

            # Update files info
            for i in range(file_storage.num_files()):
                # Get file size
                size_bytes = file_storage.file_size(i)
                size_str = self._format_size(size_bytes)

                # Calculate progress and remaining
                progress = 0
                remaining_bytes = size_bytes
                if i < len(file_progress):
                    progress_bytes = file_progress[i]
                    if size_bytes > 0:
                        progress = min(100, (progress_bytes * 100.0) / size_bytes)
                    remaining_bytes = max(0, size_bytes - progress_bytes)

                # Get priority
                priority = "Normal"  # Default
                if i < len(priorities):
                    priority = priority_map.get(priorities[i], "Normal")

                # Format remaining size
                remaining_str = self._format_size(remaining_bytes)

                # Add file info
                file_path = file_storage.file_path(i)
                file_name = os.path.basename(file_path)

                torrent_obj.files.append({
                    "name": file_name,
                    "size": size_str,
                    "progress": progress,
                    "priority": priority,
                    "remaining": remaining_str,
                    "path": file_path
                })

            # Signal that files have been updated
            self.filesUpdatedSignal.emit(torrent_obj.name)
            return True
        except Exception as e:
            print(f"Error updating files for {torrent_obj.name}: {e}")
            return False

    def run(self):
        try:
            # Check if libtorrent loaded successfully
            if lt is None:
                error_msg = "libtorrent failed to load. Please ensure Visual C++ Redistributable is installed on Windows."
                print(error_msg)
                self.errorSignal.emit(error_msg)
                return
            
            print("Initializing libtorrent session.")
            self._session = lt.session()

            # Use proper settings for modern libtorrent
            settings = {
                'listen_interfaces': '0.0.0.0:6881,[::]:6881',  # Support both IPv4 and IPv6
                'enable_dht': True,
                'enable_lsd': True,
                'enable_natpmp': True,
                'enable_upnp': True,
                'announce_to_all_trackers': True,
                'announce_to_all_tiers': True,
                'connections_limit': 500,  # Increased for better performance
                #'connections_limit_per_torrent': 200,  # Per torrent limit
                'download_rate_limit': 0,  # No download limit
                'upload_rate_limit': 0,  # No upload limit (adjust if needed)
                'active_downloads': self.max_concurrent_downloads,
                'active_seeds': 10,  # Allow some seeding
                'active_limit': self.max_concurrent_downloads + 10,
                'alert_mask': lt.alert.category_t.all_categories,
                'mixed_mode_algorithm': lt.bandwidth_mixed_algo_t.prefer_tcp,
                'enable_incoming_tcp': True,
                'enable_outgoing_tcp': True,
                'enable_incoming_utp': True,
                'enable_outgoing_utp': True,
                'strict_super_seeding': False,
                'auto_manage_interval': 15,  # Check auto-managed torrents every 15 seconds
                'max_failcount': 3,  # Retry failed trackers
                'peer_connect_timeout': 15,  # Timeout for peer connections
                'request_timeout': 60,  # Request timeout
                'max_allowed_in_request_queue': 2000,  # Increase queue size
                'max_out_request_queue': 1000,
                'whole_pieces_threshold': 20,  # Download whole pieces optimization
                'use_parole_mode': True,  # Give slow peers a chance
                'prioritize_partial_pieces': False,  # For sequential downloading
                'rate_limit_utp': True,  # Rate limit uTP to avoid congestion
                'announce_double_nat': True,  # Help with NAT traversal
            }
            self._session.apply_settings(settings)

            print("Session configured with optimal settings.")

            # Add each torrent with existing resume data
            self._add_torrents(self.torrents)
            
            # Do initial concurrency management
            self._check_concurrency_limits()

            # Main loop variables
            last_save_time = time.time()
            last_check_new_torrents = time.time()
            last_ui_update = time.time()

            while not self._stop:
                st_all = []
                active_torrents = list(self._handles.items())
                current_time = time.time()

                # Process alerts first to get any resume data responses
                alerts = self._session.pop_alerts()
                for alert in alerts:
                    if isinstance(alert, lt.save_resume_data_alert):
                        tor_handle = alert.handle
                        for t_name, (t_obj, h_obj) in self._handles.items():
                            if h_obj == tor_handle:
                                resume_data = lt.write_resume_data_buf(alert.params)
                                save_resume_to_file(t_obj, resume_data)
                                break
                    elif isinstance(alert, lt.save_resume_data_failed_alert):
                        print(f"Save resume data failed: {alert.message()}")
                    # Handle other important alerts
                    elif isinstance(alert, lt.metadata_received_alert):
                        # Update files when metadata is received
                        tor_handle = alert.handle
                        for t_name, (t_obj, h_obj) in self._handles.items():
                            if h_obj == tor_handle:
                                self._update_torrent_files(t_obj, h_obj)
                                break
                    elif isinstance(alert, lt.torrent_checked_alert):
                        tor_handle = alert.handle
                        # Find the torrent that was checked
                        for t_name, (t_obj, h_obj) in list(self._handles.items()):
                            if h_obj == tor_handle:
                                print(f"[DEBUG] Received torrent_checked_alert for: {t_name}, current status: {t_obj.status}")
                                
                                # Only process if torrent was in verifying state
                                if getattr(t_obj, "recheck_performed", False):
                                    s = h_obj.status()
                                    print(f"[DEBUG] Progress: {s.progress}, Seeding: {s.is_seeding}")
                                    
                                    if s.progress >= 0.998 or s.is_seeding:
                                        print(f"Torrent '{t_name}' verified successfully, removing it.")
                                        # Mark as completed and remove
                                        t_obj.status = "completed"
                                        
                                        # Remove from session
                                        try:
                                            self._session.remove_torrent(h_obj, 0)  # Don't delete files
                                        except Exception as e:
                                            print(f"Error removing torrent from session: {e}")
                                        
                                        # Clean up tracking
                                        del self._handles[t_name]
                                        self._paused_torrents.discard(t_name)
                                        self._stalled_torrents.discard(t_name)
                                        
                                        # Delete resume file
                                        delete_resume_file(t_obj)
                                        
                                        # Remove from torrents list
                                        self.torrents = [t for t in self.torrents if t.name != t_name]
                                        
                                        # Update active downloads count
                                        if t_obj.status == "downloading":
                                            self._active_downloads = max(0, self._active_downloads - 1)
                                        
                                        # Emit completion signal
                                        self.torrentComplete.emit([t_obj])
                                        
                                        # Check if we can start any stalled torrents
                                        self._manage_download_queue()
                                        
                                    else:
                                        print(f"Torrent '{t_name}' verification failed, resuming download.")
                                        t_obj.status = "downloading"
                                        h_obj.resume()
                                        # Clear the recheck flag
                                        t_obj.recheck_performed = False
                                break
                # Check for new torrents (every 2 seconds)
                if current_time - last_check_new_torrents > 2:
                    if hasattr(self, 'parent') and hasattr(self.parent, 'torrent_to_add') and self.parent.torrent_to_add:
                        print(f"Found {len(self.parent.torrent_to_add)} new torrents to add")
                        new_torrents = self.parent.torrent_to_add.copy()
                        self.parent.torrent_to_add = []
                        self._add_torrents(new_torrents)
                        self.torrents.extend(new_torrents)
                    last_check_new_torrents = current_time

                # Update UI less frequently to reduce CPU usage (every 1 second)
                if current_time - last_ui_update > 1:
                    # Process each active torrent for UI updates
                    for torrent_name, (torrent_obj, handle) in active_torrents:
                        try:
                            if not handle.is_valid():
                                continue
                            
                            s = handle.status()

                            # Update torrent object (optimized for libtorrent 2.0+)
                            torrent_obj.progress = s.progress * 100
                            torrent_obj.dl_speed = s.download_rate / 1024
                            torrent_obj.ul_speed = s.upload_rate / 1024
                            torrent_obj.seeds = s.num_seeds
                            torrent_obj.peers = s.num_peers

                            # Calculate ETA
                            eta = 0
                            if s.download_rate > 0:
                                remaining_bytes = s.total_wanted - s.total_wanted_done
                                eta = int(remaining_bytes / s.download_rate) if remaining_bytes > 0 else 0
                            torrent_obj.eta = eta

                            # Determine status with better accuracy
                            old_status = torrent_obj.status
                            if torrent_name in self._paused_torrents:
                                status = "paused"
                            elif torrent_name in self._stalled_torrents:
                                status = "stalled"
                            elif s.is_seeding:
                                status = "seeding"
                            elif torrent_obj.progress >= 99.9:
                                status = "completed"
                            elif s.state == lt.torrent_status.downloading:
                                status = "downloading"
                            elif s.state == lt.torrent_status.checking_files:
                                status = "verifying"
                            else:
                                status = "downloading"  # Default fallback

                            # Update active download count based on status changes
                            if old_status == "downloading" and status != "downloading":
                                self._active_downloads = max(0, self._active_downloads - 1)
                            elif old_status not in ["downloading", "verifying"] and status == "downloading":
                                self._active_downloads += 1

                            torrent_obj.status = status
                            torrent_obj.size = self._format_size(s.total_wanted)

                            # Trigger verification for completed torrents (only once)
                            if (torrent_obj.progress >= 99.9 or s.is_seeding) and status not in ["verifying", "seeding"] and not getattr(torrent_obj, "recheck_performed", False):
                                print(f"[DEBUG] Force Recheck for: {torrent_obj.name}, current status: {torrent_obj.status}")
                                torrent_obj.status = "verifying"
                                torrent_obj.recheck_performed = True
                                handle.force_recheck()
                                
                            # Update UI
                            self.progressSignal.emit(
                                torrent_name, 
                                torrent_obj.progress, 
                                status, 
                                torrent_obj.dl_speed, 
                                torrent_obj.ul_speed, 
                                torrent_obj.eta
                            )

                            st_all.append(torrent_obj.progress >= 100)

                            # Update files list if needed (check for metadata availability)
                            try:
                                if handle.torrent_file():
                                    self._update_torrent_files(torrent_obj, handle)
                            except:
                                pass  # Metadata not available yet

                        except Exception as e:
                            print(f"Error updating status for {torrent_name}: {e}")
                    self._check_concurrency_limits()
                    last_ui_update = current_time

                # Save resume data periodically (every 60 seconds)
                if current_time - last_save_time > 60:
                    self._save_all_resume_data()
                    # Also save to JSON file
                    if hasattr(self, 'parent') and hasattr(self.parent, 'saveTorrent'):
                        self.parent.saveTorrent()
                    last_save_time = current_time

                # Sleep to reduce CPU usage (reduced for better responsiveness)
                time.sleep(0.05)

            # Final save before exiting
            self._save_all_resume_data()
            # Save to JSON to ensure latest state is preserved
            if hasattr(self, 'parent') and hasattr(self.parent, 'saveTorrent'):
                self.parent.saveTorrent()

            print("Emitting exitSignal.")
            self.exitSignal.emit(self.torrents)

        except Exception as e:
            print(f"Error in TorrentThread main loop: {e}")
            self.errorSignal.emit(str(e))
            # Try to continue gracefully
            time.sleep(1)
            if not self._stop:
                print("Attempting to continue after error...")
            else:
                return
            
    def _check_concurrency_limits(self):
        """Check concurrency limits and stall/start torrents as needed"""
        # Count current active downloads
        active_downloading = 0
        stalled_torrents = []
        
        # Get current status of all torrents
        for torrent_name, (torrent_obj, handle) in list(self._handles.items()):
            try:
                if not handle.is_valid():
                    continue
                    
                # Skip paused torrents
                if torrent_name in self._paused_torrents:
                    continue
                    
                # Skip completed/seeding torrents
                if torrent_obj.status in ["completed", "seeding", "verifying"]:
                    continue
                
                # Count active downloads
                if torrent_obj.status == "downloading":
                    active_downloading += 1
                elif torrent_obj.status == "stalled" or torrent_obj.progress < 99.9:
                    stalled_torrents.append((torrent_name, torrent_obj, handle))
                    
            except Exception as e:
                print(f"Error checking torrent {torrent_name}: {e}")
                continue
        
        # Update our tracking
        self._active_downloads = active_downloading
        
        # If we're over the limit, stall some torrents
        if active_downloading > self.max_concurrent_downloads:
            # Find torrents to stall (prefer newest ones)
            to_stall = []
            current_downloading = []
            
            for torrent_name, (torrent_obj, handle) in self._handles.items():
                if torrent_obj.status == "downloading" and torrent_name not in self._paused_torrents:
                    current_downloading.append((torrent_name, torrent_obj, handle))
            
            # Sort by name to have consistent stalling order
            current_downloading.sort(key=lambda x: x[0])
            
            # Stall excess torrents
            excess = active_downloading - self.max_concurrent_downloads
            for i in range(excess):
                if i < len(current_downloading):
                    torrent_name, torrent_obj, handle = current_downloading[-(i+1)]  # Stall from end
                    try:
                        handle.pause()
                        torrent_obj.status = "stalled"
                        self._stalled_torrents.add(torrent_name)
                        self._active_downloads -= 1
                        print(f"Stalled torrent due to concurrency limit: {torrent_name}")
                    except Exception as e:
                        print(f"Error stalling torrent {torrent_name}: {e}")
        
        # If we're under the limit, start some stalled torrents
        elif active_downloading < self.max_concurrent_downloads and stalled_torrents:
            can_start = min(len(stalled_torrents), self.max_concurrent_downloads - active_downloading)
            
            for i in range(can_start):
                torrent_name, torrent_obj, handle = stalled_torrents[i]
                try:
                    handle.resume()
                    torrent_obj.status = "downloading"
                    self._stalled_torrents.discard(torrent_name)
                    self._active_downloads += 1
                    print(f"Started previously stalled torrent: {torrent_name}")
                except Exception as e:
                    print(f"Error starting torrent {torrent_name}: {e}")
            
    def _add_torrents(self, torrents):
        """Add torrents to the session with proper resume support"""
        print(f"Adding {len(torrents)} torrents to session...")

        for torrent_obj in torrents:
            try:
                # Skip if we already have a handle for this torrent
                if torrent_obj.name in self._handles:
                    print(f"Handle for {torrent_obj.name} already exists, skipping")
                    continue
                
                # Process magnet link
                print(f"Processing magnet link for {torrent_obj.name}")
                magnet_uri = torrent_obj.magnet

                params = lt.add_torrent_params()
                params.save_path = torrent_obj.path
                params.url = magnet_uri

                # Add resume data if available
                resume_binary = load_resume_from_file(torrent_obj)
                if resume_binary:
                    try:
                        params = lt.read_resume_data(resume_binary)
                        params.save_path = torrent_obj.path
                        params.url = magnet_uri
                        print(f"Loaded resume data from file for {torrent_obj.name}")
                    except Exception as e:
                        print(f"Error loading resume data for {torrent_obj.name}: {e}")

                # Set optimal flags for libtorrent 2.0+
                params.flags |= lt.torrent_flags.auto_managed
                params.flags |= lt.torrent_flags.duplicate_is_error
                params.flags |= lt.torrent_flags.update_subscribe
                # Enable sequential download for better streaming
                params.flags |= lt.torrent_flags.sequential_download
                # Optimize for faster downloads
                params.flags &= ~lt.torrent_flags.paused  # Ensure not paused by default
                params.flags &= ~lt.torrent_flags.apply_ip_filter  # Don't apply IP filter for speed

                # Add the torrent
                print(f"Adding torrent {torrent_obj.name} with save_path={torrent_obj.path}")
                handle = self._session.add_torrent(params)

                # Set high priority for faster downloading
                handle.set_priority(255)  # Highest priority
                
                # Set appropriate torrent state
                if torrent_obj.status == "paused":
                    handle.pause()
                    self._paused_torrents.add(torrent_obj.name)
                else:
                    handle.resume()
                    # Force start if not over concurrency limit
                    if self._active_downloads < self.max_concurrent_downloads:
                        handle.resume()
                        if torrent_obj.progress < 99.9:
                            self._active_downloads += 1

                # Store the handle
                self._handles[torrent_obj.name] = (torrent_obj, handle)
                print(f"Successfully added torrent {torrent_obj.name}")
                
            except Exception as e:
                print(f"Error adding torrent {torrent_obj.name}: {e}")
                
        # After adding all torrents, check concurrency limits
        self._check_concurrency_limits()

    def _save_all_resume_data(self):
        """Request resume data for all torrents with proper error handling"""
        print("Saving resume data for all torrents...")
        for torrent_name, (torrent_obj, handle) in list(self._handles.items()):
            try:
                if handle.is_valid():
                    # Check if we have metadata before requesting resume data
                    try:
                        torrent_file = handle.torrent_file()
                        if torrent_file:
                            # Use flags for high quality resume data
                            flags = lt.save_resume_flags_t.save_info_dict | lt.save_resume_flags_t.only_if_modified
                            handle.save_resume_data(flags)
                            print(f"Requested resume data for {torrent_name}")
                        else:
                            print(f"Metadata not available yet for {torrent_name}")
                    except:
                        print(f"Metadata not available yet for {torrent_name}")
            except Exception as e:
                print(f"Error requesting resume data for {torrent_name}: {e}")