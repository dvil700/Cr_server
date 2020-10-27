function UrlDispatcher(app_name) {
    this.app_name = app_name;

    this.service_group_url = function (service_group_id = null) {
        let url = '/' + this.app_name + '/service_groups/';
        url += (service_group_id) ? service_group_id : 'new';
        return url;
    }

    this.post_settings_url = function (service_group_id = null) {
        let url = '/' + this.app_name + '/service_groups/';
        url += (service_group_id) ? service_group_id : '';
        return url;
    }

    this.get_driver_form_url = function (driver_name, service_group_id = null) {
        let url = '/' + this.app_name + '/driver_forms/' + driver_name;
        url += service_group_id ? ('?service_group_id=' + service_group_id) : '';
        return url;

    }

    this.get_allowed_users_url = function (service_group_id) {
        return this.service_group_url(service_group_id) + '/allowed_users/'
    }

    this.get_device_change_state_url = function (service_group_id) {
        return '/' + this.app_name + '/service_groups/' + service_group_id + '/fiscal_device/';
    }
}


function SettingsFormManager(url_dispatcher, modal_window_builder) {
    this.url_dispatcher = url_dispatcher;
    this.modal_window_builder = modal_window_builder;

    this._save_success = function (modal, data, textStatus) {
        $(modal).modal('hide');
        modal.parentNode.removeChild(modal);
        window.location.reload();

    }

    this._save_fail = function (modal) {
        alert('Отсутствует соединение с сервером. Повторите попытку позже.');

    }

    this.save_data = function (modal, service_group_id = null) {
        let data = $('#service-group-settings-form').serialize();
        $.ajax({
            url: url_dispatcher.post_settings_url(service_group_id), method: "POST", data: data, context: this,
            success: function (data, textStatus) { this._save_success(modal, data, textStatus) },
            fail: function () { this._save_fail(modal); }
        });
    }


    this._load_success = function (service_group_id, data, textStatus) {
        let modal = this.modal_window_builder.create('', data);
        document.body.insertBefore(modal, document.querySelector('.container'));

        let button_save = modal.querySelector('.btn-primary')
        button_save.addEventListener('click', {
            handleEvent: function () { this.form_manager.save_data(modal, service_group_id); },
            form_manager: this
        });

        let driver_select_field = modal.querySelector('.settings-driver-name select');
        driver_select_field.addEventListener('change', {
            handleEvent: function (event) {
                this.form_manager.load_driver_settings_form(modal, service_group_id);
            }, 'form_manager': this, 'modal': modal
        });

        $(modal).modal('show');
    }

    this._load_fail = function () {
        alert('Отсутствует соединение с сервером. Повторите попытку позже.');

    }

    this.load = function (service_group_id = null) {
        $.ajax({
            url: this.url_dispatcher.service_group_url(service_group_id), dataType: 'html', context: this,
            success: function (data, textStatus) { this._load_success(service_group_id, data, textStatus) },
            fail: function () { this._load_fail(); }
        });
    }


    this.load_driver_settings_form = function (modal, service_group_id = null) {
        driver_name = modal.querySelector('.settings-driver-name select').value;
        console.log(modal.querySelector('.settings-driver-name select').value);
        if (!driver_name) {
            modal.querySelector('.driver-settings-form').innerHTML = '';
            return;
        }
        $.ajax({
            url: this.url_dispatcher.get_driver_form_url(driver_name, service_group_id), dataType: "html",
            success: function (data, textStatus) {
                modal.querySelector('.driver-settings-form').innerHTML = data;
            }
        });

    }
}



function AccessFormManager(url_dispatcher, modal_window_builder) {
    this.url_dispatcher = url_dispatcher;
    this.modal_window_builder = modal_window_builder;

    this.load = function (service_group_id) {
        $.ajax({
            url: this.url_dispatcher.get_allowed_users_url(service_group_id), dataType: 'html', context: this,
            success: function (data, textStatus) { this._load_success(service_group_id, data, textStatus) },
            fail: function () { this._load_fail(); }
        });
    }

    this._load_fail = function () {
        alert('Отсутствует соединение с сервером. Повторите попытку позже.');
    }

    this._load_success = function (service_group_id, data, textStatus) {
        let modal = this.modal_window_builder.create('', data);
        document.body.insertBefore(modal, document.querySelector('.container'));

        let button_save = modal.querySelector('.modal-footer').querySelector('.btn-primary')
        button_save.addEventListener('click', {
            handleEvent: function () { this.form_manager.save_data(modal, service_group_id); },
            form_manager: this
        });

        let add_button = modal.querySelector('.add-user-button');
        let remove_button = modal.querySelector('.remove-user-button');

        let all_users_list = modal.querySelector('.all-users-list');
        let added_users_list = modal.querySelector('.added-users-list');


        add_button.addEventListener('click', function () {
            let active_item = all_users_list.querySelector('.active');

            if (!active_item) {
                return
            }
            all_users_list.removeChild(active_item);
            added_users_list.appendChild(active_item);
            active_item.classList.remove('active');
        });

        remove_button.addEventListener('click', function () {
            let active_item = added_users_list.querySelector('.active');
            if (!active_item) {
                return
            }
            added_users_list.removeChild(active_item);
            all_users_list.appendChild(active_item);
            active_item.classList.remove('active');
        });

        $(modal).modal('show');
    }

    this._save_success = function (modal, data, textStatus) {
        $(modal).modal('hide');
        modal.parentNode.removeChild(modal);

    }

    this._save_fail = function (modal) {
        alert('Отсутствует соединение с сервером. Повторите попытку позже.');

    }

    this.save_data = function (modal, service_group_id) {
        let node_list = modal.querySelector('.added-users-list').querySelectorAll('.list-group-item');
        let csrf_token = modal.querySelector('#csrf_token').value;
        let resource_users = [];
        let digits_re = /[a-zA-z]+-(\d+)$/
        for (let i = 0; i < node_list.length; i++) {
            resource_users.push(digits_re.exec(node_list[i].id)[1]);
        }

        let data = JSON.stringify({ 'resource_users': resource_users, 'csrf_token': csrf_token });
        $.ajax({
            url: this.url_dispatcher.get_allowed_users_url(service_group_id), method: "POST", data: data, context: this,
            contentType: 'application/json',
            success: function (data, textStatus) { this._save_success(modal, data, textStatus) },
            fail: function () { this._save_fail(modal); }
        });
    }
}


function AbstractDeviceState() {
    this.service_group = null;
    this.set_service_group = function (service_group) {
        this.service_group = service_group;
    }

    this.run = function () { };
    this.stop = function () { };
    this.reboot = function () { };
}

function BaseDeviceState(url_dispatcher) {
    AbstractDeviceState.call(this);
    this.url_dispatcher = url_dispatcher;
    this._success = function (response) { }
    this._fail = function (response) { };
    this._request = function (state_name) {
        $.ajax({
            url: this.url_dispatcher.get_device_change_state_url(this.service_group.id),
            method: "POST",
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify({ 'state': state_name, 'csrf_token': this.service_group.get_csrf() }),
            context: this,
            success: function (response) {
                console.log(response);
                this.service_group.set_csrf(response.csrf_token);
                this._success(response);
            },
            fail: function (response) {
                this.fail(response);
            }
        });
    }
}
BaseDeviceState.prototype = Object.create(AbstractDeviceState.prototype);


function StoppedDeviceState(url_dispatcher) {
    BaseDeviceState.call(this, url_dispatcher);
    this.set_service_group = function (service_group) {
        this.service_group = service_group;
        this.service_group.device_stopped();
    }

    this._success = function (response) {
        this.service_group.set_device_state(new RunningDeviceState(this.url_dispatcher))
    };
    this._fail = function (response) {

    };

    this.run = function () {
        this._request('running');
    };

}
StoppedDeviceState.prototype = Object.create(BaseDeviceState.prototype);


function RunningDeviceState(url_dispatcher) {
    BaseDeviceState.call(this, url_dispatcher);
    this.set_service_group = function (service_group) {
        this.service_group = service_group;
        this.service_group.device_running();
    }

    this.is_rebooting = null;

    this._success = function (response) {
        if (this.is_rebooting) {
            this.is_rebooting = null;
            return;
        }
        this.service_group.set_device_state(new StoppedDeviceState(this.url_dispatcher));
    };
    this._fail = function (response) {
        this.is_rebooting = null;
    };

    this.stop = function () {
        this._request('stopped');
    };

    this.reboot = function () {
        this.is_rebooting = true;
        this._request('reboot');
    };

}
RunningDeviceState.prototype = Object.create(BaseDeviceState.prototype);


function StateDoesNotExistError(message) {
    this.message = message;
    this.name = 'StateDoesNotExistError';
}


function StateFactory(url_dispatcher) {
    this.state_map = { 'включено': RunningDeviceState, 'выключено': StoppedDeviceState }
    this.url_dispatcher = url_dispatcher;
    this.get_state = function (service_group_dom_element) {
        let state_str = service_group_dom_element.querySelector('.device-state').textContent.toLowerCase().trim();
        for (let key in this.state_map) {
            if (key == state_str) {
                return new this.state_map[key](this.url_dispatcher);
            }
        }
        throw new StateDoesNotExistError('"' + state_str + '" is not a valid state signature');
    }
}


function ServiceGroupView(dom_element) {
    this.dom_element = dom_element;
    this._device_run_event_handler = null;
    this._device_stop_event_handler = null;
    this._service_group_delete_event_handler = null;

    this.get_id = function () {
        return this.dom_element.querySelector('.service-group-id').textContent.trim()
    }

    this.set_show_settings_event = function (handler) {
        let show_settings_button = this.dom_element.querySelector('.settings');
        show_settings_button.addEventListener('click', handler);
    }

    this.set_show_access_settings_event = function (handler) {
        let show_settings_button = this.dom_element.querySelector('.access-settings');
        show_settings_button.addEventListener('click', handler);
    }

    this.set_device_run_event_handler = function (handler) {
        this._device_run_event_handler = handler;
    }

    this.set_device_stop_event_handler = function (handler) {
        this._device_stop_event_handler = handler;
    }

    this.set_service_group_delete_event_handler = function (handler) {
        this._service_group_delete_event_handler = handler;
        let delete_link = this.dom_element.querySelector('.delete');
        delete_link.addEventListener('click', handler);
    }

    this.device_running = function () {
        let state_change_button = this.dom_element.querySelector('.button-change-device-state');

        state_change_button.classList.remove("btn-success");
        state_change_button.classList.add("btn-danger");
        let state_text = this.dom_element.querySelector('.device-state');
        state_text.classList.remove("text-danger");
        state_text.classList.add("text-success");
        state_text.textContent = 'Включено';
        state_change_button.textContent = 'Стоп';
        state_change_button.addEventListener('click', this._device_stop_event_handler, { once: true });

    }

    this.device_stopped = function () {
        let state_change_button = this.dom_element.querySelector('.button-change-device-state');
        state_change_button.classList.remove("btn-danger");
        state_change_button.classList.add("btn-success");
        let state_text = this.dom_element.querySelector('.device-state');
        state_text.classList.remove("text-success");
        state_text.classList.add("text-danger");
        state_text.textContent = 'Выключено';
        state_change_button.textContent = 'Пуск';
        state_change_button.addEventListener('click', this._device_run_event_handler, { once: true });
    }

}

function ServiceGroupActionManager(url_dispatcher) {
    this.url_dispatcher = url_dispatcher;
    this.delete_service_group = function (service_group) {
        $.ajax({
            url: url_dispatcher.service_group_url(service_group.id), method: "DELETE", context: this,
            success: function (data, textStatus) { window.location.reload() },
            fail: function () { alert('Отсутствует соединение с сервером. Повторите попытку позже.'); }
        });
    }
}



function ServiceGroup(service_group_view, csrf_object, settings_form_manager, access_form_manager, action_manager) {
    this.view = service_group_view;
    this.id = service_group_view.get_id();
    this.csrf_object = csrf_object;
    this.device_state = null;
    this.settings_form_manager = settings_form_manager;
    this.access_form_manager = access_form_manager;
    this.action_manager = action_manager;

    // init buttons
    this.view.set_show_settings_event({ handleEvent: function (e) { this.sg.show_settings(); }, 'sg': this });
    this.view.set_show_access_settings_event({ handleEvent: function (e) { this.sg.show_access_settings(); }, 'sg': this });

    this.view.set_device_run_event_handler({ handleEvent: function (e) { this.sg.device_run(); }, 'sg': this });
    this.view.set_device_stop_event_handler({ handleEvent: function (e) { this.sg.device_stop(); }, 'sg': this });
    this.view.set_service_group_delete_event_handler({ handleEvent: function (e) { this.sg.delete(); }, 'sg': this });

    this.set_device_state = function (device_state) {
        this.device_state = device_state;
        this.device_state.set_service_group(this);
    };

    this.get_csrf = function () {
        return this.csrf_object.get_csrf();
    }

    this.set_csrf = function (value) {
        return this.csrf_object.set_csrf(value);
    }

    this.device_run = function () {
        this.device_state.run();
    };

    this.device_stop = function () {
        this.device_state.stop();
    }

    this.device_running = function () {
        this.view.device_running();
    }

    this.device_stopped = function () {
        this.view.device_stopped();
    }

    this.device_reboot = function () {
        this.device_state.reboot();
    }

    this.show_settings = function () {
        this.settings_form_manager.load(this.id);
    }

    this.show_access_settings = function () {
        this.access_form_manager.load(this.id);
    }

    this.delete = function () {
        this.action_manager.delete_service_group(this);

    }

}