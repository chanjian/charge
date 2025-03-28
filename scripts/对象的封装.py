class Response(object):
    def __init__(self):
        self.status = True
        self.detail = 999
        self.data = [11,22,33]
    @property
    def dict(self):
        return self.__dict__

obj = Response()
print(obj.dict)