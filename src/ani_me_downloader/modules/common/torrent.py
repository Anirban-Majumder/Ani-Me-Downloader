class Torrent:
    def __init__(self, name="", magnet="", path="",anime_id=0, status="paused"):
        self.name = name
        self.magnet = magnet
        self.path = path
        self.anime_id = anime_id
        self.status = status
        self.files = []  # Will store file data: name, size, progress, priority, remaining
        self.size = "0 MB"
        self.seeds = 0
        self.peers = 0
        self.dl_speed = 0
        self.ul_speed = 0
        self.eta = 0
        self.progress = 0
        self.recheck_performed = False
        self.handle = None  # To store libtorrent handle
        self.is_queued = False  # Track if torrent is in queue but not yet added to session

    def to_dict(self):
        return {
            'name': self.name,
            'magnet': self.magnet,
            'path': self.path,
            'anime_id': self.anime_id,
            'status': self.status,
            'files': self.files,
            'size': self.size,
            'progress': self.progress,
            'eta': self.eta,
            'recheck_performed': self.recheck_performed,
            'is_queued': getattr(self, 'is_queued', False)
        }

    @classmethod
    def from_dict(cls, data):
        # Handle resume data carefully
        torrent = cls(
            name=data.get('name', ''),
            magnet=data.get('magnet', ''),
            path=data.get('path', ''),
            anime_id=data.get('anime_id', 0),
            status=data.get('status', 'paused')
        )

        # Set additional properties
        torrent.files = data.get('files', [])
        torrent.size = data.get('size', '0 MB')
        torrent.eta = data.get('eta', 0)
        torrent.progress = data.get('progress', 0)
        torrent.recheck_performed = data.get('recheck_performed', False)
        torrent.is_queued = data.get('is_queued', False)
        return torrent