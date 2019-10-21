import aiomysql
import re


class DBaseMeta(type):
    def __call__(cls, *a, **k):
        if not getattr(cls, '_instance', None):
            cls._instance = super().__call__(*a, **k)
        return cls._instance


class Data_base(metaclass=DBaseMeta):
    @classmethod
    async def connect(cls, config, loop):
        pool = await aiomysql.create_pool(**config, loop=loop, autocommit=True)
        return cls(pool)
        
    def __init__(self, pool=None):
       if pool:
           self.pool=pool
       
 
    async def query(self, request, params, rows=False):  
        result=False
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(request, params)
                if re.match(r'^\s*insert', request, flags=re.IGNORECASE) is not None:
                    return cur.lastrowid
                if rows:
                    result = await cur.fetchall()
                else:
                    result = await cur.fetchone()
                return result

    

    async def close(self):
        self.pool.close()
        await self.pool.wait_closed()
        self.__class__._instance=None



  





     

  

