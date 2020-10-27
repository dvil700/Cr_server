function UserUrlDispatcher(app_name){
    this.app_name = app_name;

    this.get_user_settings_form_url = function(user_id=null){
      let url = '/'+this.app_name+'/users/';
      url += (user_id)?user_id:'new';
      return url;
    }

    this.user_url = function(user_id=null){
      let url = '/'+this.app_name+'/users/';
      url += (user_id)?user_id:'';
      return url;
    }
}



function UserSettingsFormManager(url_dispatcher, modal_window_builder){
    this.url_dispatcher = url_dispatcher;
    this.modal_window_builder = modal_window_builder;

    this._save_success = function(modal, data, textStatus){
      $(modal).modal('hide');
      modal.parentNode.removeChild(modal);
      window.location.reload();
        
    }

    this._save_fail = function(modal){
      alert('Отсутствует соединение с сервером. Повторите попытку позже.');

    }

    this.save_data = function(modal, user_id=null){
      let data = $('#user-settings-form').serialize();
      $.ajax({url: url_dispatcher.user_url(user_id), method: "POST", data: data, context: this,
              success: function(data, textStatus){this._save_success(modal, data, textStatus)}, 
              fail: function(){this._save_fail(modal);}});
    }


    this._load_success = function(user_id, data, textStatus){
      let modal = this.modal_window_builder.create('', data);
      document.body.insertBefore(modal, document.querySelector('.container'));

      let button_save = modal.querySelector('.btn-primary')
      button_save.addEventListener('click', {handleEvent: function(){this.form_manager.save_data(modal, user_id);},
                                            form_manager: this});
      
      $(modal).modal('show');
    }
    
    this._load_fail = function(){
      alert('Отсутствует соединение с сервером. Повторите попытку позже.');

    }

    this.load = function(user_id=null){
      $.ajax({url: this.url_dispatcher.get_user_settings_form_url(user_id), dataType: 'html', context: this,  
              success: function(data, textStatus){this._load_success(user_id, data, textStatus)}, 
              fail: function(){this._load_fail();}});
    }

}

function UserView(dom_element){
    this.dom_element = dom_element;

    this.get_id = function(){
      return this.dom_element.querySelector('.user-id').textContent.trim()
    }

    this.set_show_settings_event = function(handler){
      let show_settings_button = this.dom_element.querySelector('.settings');
      show_settings_button.addEventListener('click', handler);
    }

    this.set_delete_event = function(handler){
      let delete_link = this.dom_element.querySelector('.delete');
      delete_link.addEventListener('click', handler);
    }

    
  }

  
function UserActionManager(url_dispatcher){
this.url_dispatcher = url_dispatcher;
this.delete_user = function(user){
  $.ajax({url: url_dispatcher.user_url(user.id), method: "DELETE", context: this,
              success: function(data, textStatus){window.location.reload()}, 
              fail: function(){alert('Отсутствует соединение с сервером. Повторите попытку позже.');}});
   
}
}

function User(user_view, csrf_object, settings_form_manager, action_manager){
    this.view = user_view;
    this.id = user_view.get_id();
    this.csrf_object = csrf_object;
    this.device_state = null;
    this.settings_form_manager = settings_form_manager;
    this.action_manager =  action_manager;

    // init actions
    this.view.set_show_settings_event({handleEvent: function(e){this.user.show_settings();}, 'user': this});
    this.view.set_delete_event({handleEvent: function(e){this.user.delete();}, 'user': this});
    
    this.get_csrf = function(){
      return this.csrf_object.get_csrf();
    }

    this.set_csrf = function(value){
      return this.csrf_object.set_csrf(value);
    }


    this.show_settings = function(){
      this.settings_form_manager.load(this.id);
    }
    

    this.delete = function(){
      this.action_manager.delete_user(this);
      
    }


  }