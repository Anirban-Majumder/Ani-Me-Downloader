from PyQt5.QtCore import QThread, pyqtSignal
from ..common.utils import Constants, check_network
import libtorrent as lt
import time, os, math
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
            if torrent_obj.status != "paused":
                handle.pause()
                # If the torrent was seeding when paused, mark it as completed
                if torrent_obj.status == "seeding":
                    torrent_obj.status = "completed"
                else:
                    torrent_obj.status = "paused"
                self._paused_torrents.add(torrent_name)
                
                # Decrease active download count if this was downloading
                if torrent_obj.status == "downloading":
                    self._active_downloads = max(0, self._active_downloads - 1)
                    self._manage_download_queue()  # Check if we can start any stalled torrents
                
                return True
        return False

    def resume_torrent(self, torrent_name):
        """Resume a specific torrent by name"""
        if torrent_name in self._handles:
            torrent_obj, handle = self._handles[torrent_name]
            if torrent_obj.status == "paused":
                # Check if we have room for another active download
                if torrent_obj.progress < 99.9 and self._active_downloads >= self.max_concurrent_downloads:
                    # Mark as stalled instead of starting it
                    torrent_obj.status = "stalled"
                    if torrent_name in self._paused_torrents:
                        self._paused_torrents.remove(torrent_name)
                    self._stalled_torrents.add(torrent_name)
                    return True
                
                handle.resume()
                # Determine proper status based on progress
                if torrent_obj.progress >= 99.9:
                    torrent_obj.status = "seeding"
                else:
                    torrent_obj.status = "downloading"
                    self._active_downloads += 1
                
                if torrent_name in self._paused_torrents:
                    self._paused_torrents.remove(torrent_name)
                if torrent_name in self._stalled_torrents:
                    self._stalled_torrents.remove(torrent_name)
                return True
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
            print("Initializing libtorrent session.")
            self._session = lt.session()

            # Use proper settings for modern libtorrent
            settings = {
                'listen_interfaces': '0.0.0.0:6881',  # Modern way to set listen port
                'enable_dht': True,
                'enable_lsd': True,
                'enable_natpmp': True,
                'enable_upnp': True,
                'announce_to_all_trackers': True,
                'announce_to_all_tiers': True,
                'connections_limit': 200,
                'alert_mask': lt.alert.category_t.all_categories
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
                        # Gather torrent names to remove after iteration
                        to_remove = []
                        to_remove_obj = []
                        for t_name, (t_obj, h_obj) in self._handles.items():
                            if h_obj == tor_handle:
                                print(f"[DEBUG] Received torrent_checked_alert for: {t_name}, current status: {t_obj.status}")
                                # Only process if torrent was in verifying state
                                if getattr(t_obj, "recheck_performed", False):
                                    s = h_obj.status()
                                    print(f"[DEBUG] Progress: {s.progress}, Seeding: {s.is_seeding}")
                                    if s.progress >= 1.0 or s.is_seeding:
                                        print(f"Torrent '{t_name}' verified successfully, removing it.")
                                        to_remove.append(t_name)
                                        to_remove_obj.append(t_obj)
                                    else:
                                        print(f"Torrent '{t_name}' verification failed, resuming download.")
                                        h_obj.resume()
                                        t_obj.status = "downloading"
                                break
                        # Remove verified torrents from _handles/torrents
                        for t_name in to_remove:
                            if t_name in self._handles:
                                try:
                                    self._paused_torrents.remove(t_name)
                                except KeyError:
                                    pass
                                try:
                                    self._stalled_torrents.remove(t_name)
                                except KeyError:
                                    pass
                                #delete the fastresume file
                                delete_resume_file([obj for obj in to_remove_obj if obj["name"] == t_name])
                                # Emit signal to update UI/anime list if desired
                                self.torrentComplete.emit(to_remove_obj)
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
                            elif s.is_seeding or torrent_obj.progress >= 100:
                                status = "completed"
                            else:
                                status = "downloading"

                            # If status changed from downloading to something else or vice versa,
                            # update active download count
                            if old_status == "downloading" and status != "downloading":
                                self._active_downloads = max(0, self._active_downloads - 1)
                            elif old_status != "downloading" and status == "downloading":
                                self._active_downloads += 1

                            torrent_obj.status = status
                            torrent_obj.size = self._format_size(s.total_wanted)

                            if ((torrent_obj.progress >= 100 or s.is_seeding) or torrent_obj.status=="completed") and torrent_obj.status != "verifying" and not getattr(torrent_obj, "recheck_performed", False):
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

                            # Update files list if needed
                            if handle.has_metadata():
                                self._update_torrent_files(torrent_obj, handle)

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

                # Sleep to reduce CPU usage
                time.sleep(0.1)

            # Final save before exiting
            self._save_all_resume_data()
            # Save to JSON to ensure latest state is preserved
            if hasattr(self, 'parent') and hasattr(self.parent, 'saveTorrent'):
                self.parent.saveTorrent()

            print("Emitting exitSignal.")
            self.exitSignal.emit(self.torrents)

        except Exception as e:
            print(f"Error in TorrentThread: {e}")
            self.errorSignal.emit(str(e))
            
    def _check_concurrency_limits(self):
        """Check concurrency limits and stall/start torrents as needed"""
        # Count active downloads
        active_count = 0
        downloading_torrents = []
        stalled_candidates = []
        
        # First pass: identify status of all torrents
        for torrent_name, (torrent_obj, handle) in self._handles.items():
            # Skip paused torrents
            if torrent_name in self._paused_torrents:
                continue
                
            # Check if it's currently downloading
            if torrent_obj.status == "downloading":
                active_count += 1
                downloading_torrents.append((torrent_name, torrent_obj, handle))
            
            # Identify torrents that can be stalled if needed
            elif torrent_obj.status == "stalled" or (torrent_obj.progress < 99.9 and 
                  torrent_obj.status not in ["completed", "seeding", "paused"]):
                stalled_candidates.append((torrent_name, torrent_obj, handle))
        
        # Update active count
        self._active_downloads = active_count
        
        # Second pass: stall torrents if over limit
        if active_count > self.max_concurrent_downloads:
            # Need to stall (active_count - self.max_concurrent_downloads) torrents
            to_stall = downloading_torrents[self.max_concurrent_downloads:]
            for torrent_name, torrent_obj, handle in to_stall:
                handle.pause()  # Pause but don't consider it user-paused
                torrent_obj.status = "stalled"
                self._stalled_torrents.add(torrent_name)
                print(f"Stalled torrent due to concurrency limit: {torrent_name}")
                self._active_downloads -= 1
        
        # Third pass: start stalled torrents if under limit
        elif active_count < self.max_concurrent_downloads and stalled_candidates:
            # We can start (self.max_concurrent_downloads - active_count) torrents
            can_start = min(len(stalled_candidates), self.max_concurrent_downloads - active_count)
            for i in range(can_start):
                torrent_name, torrent_obj, handle = stalled_candidates[i]
                handle.resume()
                torrent_obj.status = "downloading"
                if torrent_name in self._stalled_torrents:
                    self._stalled_torrents.remove(torrent_name)
                self._active_downloads += 1
                print(f"Started previously stalled torrent: {torrent_name}")
            
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
                # Enable sequential download
                params.flags |= lt.torrent_flags.sequential_download

                # Add the torrent
                print(f"Adding torrent {torrent_obj.name} with save_path={torrent_obj.path}")
                handle = self._session.add_torrent(params)

                # Set appropriate torrent state
                if torrent_obj.status == "paused":
                    handle.pause()
                    self._paused_torrents.add(torrent_obj.name)
                else:
                    handle.resume()

                # Store the handle
                self._handles[torrent_obj.name] = (torrent_obj, handle)
                print(f"Successfully added torrent {torrent_obj.name}")
                # After adding all torrents, check concurrency limits
                self._check_concurrency_limits()
            except Exception as e:
                print(f"Error adding torrent {torrent_obj.name}: {e}")

    def _save_all_resume_data(self):
        """Request resume data for all torrents with proper error handling"""
        print("Saving resume data for all torrents...")
        for torrent_name, (torrent_obj, handle) in list(self._handles.items()):
            try:
                if handle.is_valid():
                    # Check if we have metadata before requesting resume data
                    if handle.has_metadata():
                        # Use flags for high quality resume data
                        flags = lt.save_resume_flags_t.save_info_dict | lt.save_resume_flags_t.only_if_modified
                        handle.save_resume_data(flags)
                        print(f"Requested resume data for {torrent_name}")
                    else:
                        print(f"Metadata not available yet for {torrent_name}")
            except Exception as e:
                print(f"Error requesting resume data for {torrent_name}: {e}")