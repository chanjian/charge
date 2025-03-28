class Base:
    def f1(self):
        print('Base')

class Foo:
    def f1(self):
        print("Foo")
        super().f1()

class Bar(Foo,Base):
    def f1(self):
        print("Bar")
        super().f1()

obj = Foo()
obj.f1()
