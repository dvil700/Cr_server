function ModalWindowBuilder(){
    this._create_element = function(tag_name, attributes=null){
      let el = document.createElement(tag_name);
      if (attributes){
        for (key in attributes){
          el.setAttribute(key, attributes[key]);
        } 
      }
      return el;
    }
    
    this.create = function(title, content){
      let modal = this._create_element('div', {class:'modal fade', 'data-backdrop':"static", 'data-keyboard':"false", 
                                              tabindex:"-1", 'aria-labelledby':"staticBackdropLabel",  "aria-hidden":"true"});
      let modal_dialog  = this._create_element('div', {class: "modal-dialog"});
      let modal_content  = this._create_element('div', {class: "modal-content"});
      let modal_header  = this._create_element('div', {class: "modal-header"});
      let modal_title = this._create_element('div', {class: "modal-title"});
      modal_title.innerHTML = '<h5 class="modal-title">'+title+'</h5>';

      let top_close_button =  this._create_element('button', {class: "close", type: "button", "data-dismiss":"modal", 
                                                                              "aria-label":"Close"});
      top_close_button.innerHTML = '<span aria-hidden="true">x</span>';
      modal_header.appendChild(modal_title);
      modal_header.appendChild(top_close_button);
    
      let modal_body = this._create_element('div', {class: "modal-body"});
      modal_body.innerHTML = content;
    
      let modal_footer = this._create_element('div', {class: "modal-footer"});
      let bottom_close_button = this._create_element('button', {class: "btn btn-secondary", type: "button"});
      let submit_button = this._create_element('button', {class: "btn btn-primary", type: "button"});
      bottom_close_button.textContent ='Закрыть';
      submit_button.textContent = 'Сохранить';
      modal_footer.appendChild(bottom_close_button);
      modal_footer.appendChild(submit_button);

      modal.appendChild(modal_dialog).appendChild(modal_content).appendChild(modal_header);
      modal_content.appendChild(modal_body);
      modal_content.appendChild(modal_footer);

      $(modal).on('hidden.bs.modal', function (e) {
        $(e.target).remove()
      })
      return modal;
    }
  }