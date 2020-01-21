class State:
    def __init__(self, parent):
        self.parent = parent

    @property
    def executable(self):
        return False

    @property
    def value(self):
        return None

    @property
    def value_string(self):
        return self.__class__.__name__.lower()

    def represent(self):
        pass

    async def in_poccess(self):
        await self.parent.define_state(0)

    async def fail(self):
        return

    async def with_warning(self):
        return

    async def success(self):
        return


class InProccess(State):
    @property
    def executable(self):
        return True

    @property
    def value(self):
        return 0

    def represent(self):
        return self.parent.in_proccess_represent()

    async def in_poccess(self):
        return

    async def success(self):
        await self.parent.define_state(1)

    async def with_warning(self):
        await self.parent.define_state(2)

    async def fail(self):
        await self.parent.define_state(3)


class Success(State):
    @property
    def value(self):
        return 1

    def represent(self):
        return self.parent.success_represent()


class WithWarning(State):
    @property
    def value(self):
        return 2

    def represent(self):
        return self.parent.with_warning_represent()


class Fail(State):
    @property
    def value(self):
        return 3

    def represent(self):
        return self.parent.fail_represent()


state_map = [InProccess, Success, WithWarning, Fail]
