function CsrfObject(start_csrf){
    this.csrf = start_csrf;

    this.set_csrf = function(value){
      this.csrf = value;
    }
    
    this.get_csrf = function(value){
      return this.csrf;
    }

  }