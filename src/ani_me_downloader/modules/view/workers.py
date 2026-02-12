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
            try:
                anime.start()
            except Exception as e:
                print(f"Error processing anime {anime.name}: {e}")
                self.sendError.emit(f"Error checking {anime.name}: Network error")
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

    def __init__(self, torrents, command_queue):
        super().__init__()
        self.max_concurrent_downloads = cfg.maxConcurrentDownloads.value
        self.torrents = torrents
        self.command_queue = command_queue
        self._session = None
        self._handles = {}  # Map torrent name to (torrent_obj, handle)
        self._stop = False
        print("TorrentThread initialized.")

    def stop(self):
        self._stop = True

    def set_file_priorities(self, torrent_name, file_index, priority):
        """Set priority for a specific file in a torrent"""
        # This method is called directly from main thread, so need to be careful with thread safety.
        # Ideally this should also be a command in the queue, but for now we'll keep it direct
        # as it operates on the handle which is somewhat thread safe in libtorrent
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
                # 'auto_manage_interval': 5, # No longer exists in some versions, use default
                'mixed_mode_algorithm': lt.bandwidth_mixed_algo_t.prefer_tcp,
                'enable_incoming_tcp': True,
                'enable_outgoing_tcp': True,
                'enable_incoming_utp': True,
                'enable_outgoing_utp': True,
                'strict_super_seeding': False,
            }
            # For older libtorrent versions or if wrapper doesn't support dict apply
            # we use the pack_settings if available or manual apply.
            # Assuming standard python-libtorrent which supports apply_settings(dict)
            self._session.apply_settings(settings)

            print("Session configured with optimal settings.")

            # Add each torrent with existing resume data
            self._add_torrents(self.torrents)
            
            # Main loop variables
            last_save_time = time.time()
            last_ui_update = time.time()

            while not self._stop:
                # Process Command Queue
                while not self.command_queue.empty():
                    try:
                        cmd = self.command_queue.get_nowait()
                        if cmd[0] == "ADD":
                            self._add_torrents([cmd[1]])
                        elif cmd[0] == "REMOVE":
                            self._remove_torrent_internal(cmd[1], cmd[2] if len(cmd) > 2 else False)
                        elif cmd[0] == "PAUSE":
                            self._set_torrent_state(cmd[1], "paused")
                        elif cmd[0] == "RESUME":
                            self._set_torrent_state(cmd[1], "resumed")
                    except Exception as e:
                        print(f"Error processing command: {e}")

                # Wait for alerts with timeout (efficient event loop)
                self._session.wait_for_alert(100)
                
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
                                    if s.progress >= 0.998 or s.is_seeding:
                                        t_obj.status = "completed"
                                        self._remove_torrent_internal(t_name, False)
                                        self.torrentComplete.emit([t_obj])
                                    else:
                                        print(f"Torrent '{t_name}' verification failed, resuming download.")
                                        t_obj.status = "downloading"
                                        h_obj.resume()
                                        t_obj.recheck_performed = False
                                break

                current_time = time.time()

                # Update UI less frequently to reduce CPU usage (every 1 second)
                if current_time - last_ui_update > 1:
                    # Process each active torrent for UI updates
                    for torrent_name, (torrent_obj, handle) in list(self._handles.items()):
                        try:
                            if not handle.is_valid():
                                continue
                            
                            s = handle.status()

                            # Update torrent object
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

                            # Map libtorrent status to our status
                            status = "downloading" # Default
                            
                            if torrent_obj.status == "paused":
                                status = "paused" # Force paused if we manually paused it
                            elif s.is_seeding:
                                status = "seeding"
                            elif torrent_obj.progress >= 99.9:
                                status = "completed"
                            elif s.state == lt.torrent_status.checking_files:
                                status = "verifying"
                            elif s.state == lt.torrent_status.queued_for_checking:
                                status = "queued"
                            elif s.state == lt.torrent_status.downloading:
                                status = "downloading"
                            elif s.state == lt.torrent_status.finished:
                                status = "finished"
                            elif s.state == lt.torrent_status.seeding:
                                status = "seeding"
                            elif s.state == lt.torrent_status.allocating:
                                status = "allocating"
                            elif s.state == lt.torrent_status.checking_resume_data:
                                status = "checking"
                            else:
                                # For auto-managed, if it's paused by flow interactions, it's queued
                                if s.paused and s.auto_managed:
                                     status = "queued"
                                elif s.paused:
                                     status = "paused"

                            torrent_obj.status = status
                            torrent_obj.size = self._format_size(s.total_wanted)

                            # Trigger verification for completed torrents (only once)
                            if (torrent_obj.progress >= 99.9 or s.is_seeding) and status not in ["verifying", "seeding"] and not getattr(torrent_obj, "recheck_performed", False):
                                print(f"[DEBUG] Force Recheck for: {torrent_obj.name}")
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

                            # Update files list if needed (check for metadata availability)
                            try:
                                if handle.torrent_file():
                                    self._update_torrent_files(torrent_obj, handle)
                            except:
                                pass  # Metadata not available yet

                        except Exception as e:
                            print(f"Error updating status for {torrent_name}: {e}")
                    last_ui_update = current_time

                # Save resume data periodically (every 60 seconds)
                if current_time - last_save_time > 60:
                    self._save_all_resume_data()
                    last_save_time = current_time

            # Final save before exiting
            self._save_all_resume_data()

            print("Emitting exitSignal.")
            self.exitSignal.emit(self.torrents)

        except Exception as e:
            print(f"Error in TorrentThread main loop: {e}")
            self.errorSignal.emit(str(e))
            
            
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
                params.flags |= lt.torrent_flags.sequential_download
                
                # Add the torrent
                print(f"Adding torrent {torrent_obj.name} with save_path={torrent_obj.path}")
                handle = self._session.add_torrent(params)

                # Set appropriate torrent state
                if torrent_obj.status == "paused":
                    handle.unset_flags(lt.torrent_flags.auto_managed)
                    handle.pause()
                else:
                    handle.set_flags(lt.torrent_flags.auto_managed)
                    handle.resume()

                # Store the handle
                self._handles[torrent_obj.name] = (torrent_obj, handle)
                print(f"Successfully added torrent {torrent_obj.name}")
                
            except Exception as e:
                print(f"Error adding torrent {torrent_obj.name}: {e}")

    def _remove_torrent_internal(self, torrent_name, delete_files=False):
        """Internal method to remove a torrent from session"""
        if torrent_name in self._handles:
            torrent_obj, handle = self._handles[torrent_name]
            try:
                # Save resume data
                if handle.is_valid():
                    handle.save_resume_data()
                
                # Remove from session
                self._session.remove_torrent(handle, int(delete_files))
                print(f"Removed torrent {torrent_name}, delete_files={delete_files}")
                
                del self._handles[torrent_name]
                
                # Delete resume file
                delete_resume_file(torrent_obj)

                # Remove from internal list
                self.torrents = [t for t in self.torrents if t.name != torrent_name]
                return True
            except Exception as e:
                print(f"Error removing torrent: {e}")
                return False
        return False

    def _set_torrent_state(self, torrent_name, state):
        """Internal method to pause/resume torrent"""
        if torrent_name in self._handles:
            torrent_obj, handle = self._handles[torrent_name]
            try:
                if state == "paused":
                    handle.unset_flags(lt.torrent_flags.auto_managed)
                    handle.pause()
                    torrent_obj.status = "paused"
                elif state == "resumed":
                    handle.set_flags(lt.torrent_flags.auto_managed)
                    handle.resume()
                    torrent_obj.status = "downloading" # Will depend on auto-manager
                print(f"Set torrent {torrent_name} to {state}")
            except Exception as e:
                print(f"Error setting torrent state: {e}")

    def _save_all_resume_data(self):
        """Request resume data for all torrents with proper error handling"""
        # print("Saving resume data for all torrents...")
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
                    except:
                        pass
            except Exception as e:
                print(f"Error requesting resume data for {torrent_name}: {e}")