from sqlalchemy import func
from math import ceil
from aiohttp.web import HTTPNotFound


def paginator_cache(meth):
    def wrapper(self, *args, **kwargs):
        if meth.__name__ in self._cache:
            return self._cache[(meth.__name__, args, kwargs)]
        return meth(self, *args, **kwargs)

    return wrapper


class Paginator:
    def __init__(self, sqa_query, per_page, db_connection):
        self.sqa_query = sqa_query
        self.db_conn = db_connection
        self.per_page = per_page
        self._cache = {}

    @paginator_cache
    async def page(self, num):
        try:
            num = int(num)
        except:
            raise HTTPNotFound

        if num == 1 and await self.count() == 0:
            return None
        page_range = await self.page_range()
        if num not in page_range:
            raise HTTPNotFound
        values_list = await self.db_conn.query(
            self.sqa_query.offset(num - 1).limit(self.per_page).statement.apply_labels()
            , rows=True)

        return Page(values_list, num, await self.as_dict())

    @paginator_cache
    async def count(self):
        result = await self.db_conn.query(self.sqa_query.statement.with_only_columns([func.count()]))
        return result[0]

    async def num_pages(self):
        count = await self.count()
        return ceil(count / self.per_page)

    async def page_range(self):
        num_pages = await self.num_pages()
        return range(1, num_pages + 1)

    async def as_dict(self, page_num=1):
        result = dict(
            num_pages=await self.num_pages(),
            page_range=await self.page_range(),
            count=await self.count())
        return result


class Page:
    def __init__(self, values_list, num, paginator_dict):
        self.paginator = paginator_dict
        self._values_list = values_list if values_list else []
        self._num = num

    def __iter__(self):
        return self.values_list.__iter__()

    def __getitem__(self, item):
        return self.values_list[item]

    @property
    def has_next(self):
        return self._num < self.paginator['num_pages']

    @property
    def has_previous(self):
        return self._num > 1

    @property
    def number(self):
        return self._num

    @property
    def values_list(self):
        return self._values_list

    @property
    def next_page_number(self):
        if self.has_next:
            return self._num + 1

    @property
    def previous_page_number(self):
        if self.has_previous:
            return self._num - 1
