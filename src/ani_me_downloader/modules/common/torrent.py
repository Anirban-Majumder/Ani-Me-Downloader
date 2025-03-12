
class Torrent:
    def __init__(self, name="", magnet="", path="", status="paused", resume_data=None):
        self.name = name
        self.magnet = magnet
        self.path = path
        self.status = status
        self.resume_data = resume_data or b''

    def to_dict(self):
        return {
            'name': self.name,
            'magnet': self.magnet,
            'path': self.path,
            'status': self.status,
            'resume_data': self.resume_data.hex() if self.resume_data else '',
        }

    @classmethod
    def from_dict(cls, data):
        resume_data = bytes.fromhex(data['resume_data']) if data['resume_data'] else b''
        return cls(
            name=data['name'],
            magnet=data['magnet'],
            path=data['path'],
            status=data.get('status', 'paused'),
            resume_data=resume_data
        )