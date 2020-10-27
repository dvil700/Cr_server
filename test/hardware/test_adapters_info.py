import pytest
from hardware.adapters.info import PackInfo


class Test_PackInfo:
    def test_info(self):
        drivers_list = PackInfo().get_available_adapters()
        assert len(drivers_list)>=1
        assert 'test' in drivers_list