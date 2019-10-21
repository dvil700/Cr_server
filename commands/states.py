import asyncio


class State:
    @classmethod
    def define_state(self, parent, status=None):
        state_map = [In_proccess, Success, With_warning, Fail]
        if status is None:
            return state_map[0](parent)
        return state_map[int(status)](parent)

    def __init__(self, parent):
        self.parent = parent

    @property
    def executable(self):
        return False

    @property
    def value(self):
        return None

    def represent(self):
        pass

    async def in_poccess(self):
        await  self.parent.define_state(0)

    async def fail(self):
        await asyncio.sleep(0)

    async def with_warning(self):
        await asyncio.sleep(0)

    async def success(self):
        await asyncio.sleep(0)


class In_proccess(State):
    @property
    def executable(self):
        return True

    @property
    def value(self):
        return 0

    def represent(self):
        return self.parent.in_proccess_represent()

    async def in_poccess(self):
        await asyncio.sleep(0)

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


class With_warning(State):
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
