from wtforms import Form
from apps.admin.device_config_forms import create_fiscal_device_config_form


class Test:
    def test_loader(self):
        form = create_fiscal_device_config_form('test')
        assert isinstance(form, Form)
        form = create_fiscal_device_config_form('atol', settings={'cr_model': 57, 'cr_port': 1,
                                                                  'cr_ofd_channel': 2, 'cr_baudrate': '115200',
                                                                  'cr_passwd': '30', 'test_mode': 'False'})
        assert isinstance(form, Form)
        assert form.validate()