class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


def iter_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from iter_subclasses(subclass)
        yield subclass