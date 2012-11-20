//alert("admin_add_callback.js added");


django.jQuery(document).ready(function() {
	
  
  	// ============================  get hidden var passed from django =====================================
  	var obj_id = django.jQuery("#obj_id_span").attr("Value");
  
	// ============================  add callbacks to elements in page =====================================    
	var ddh = new django_dropbox_handler();
		
	//alert(django_dropbox_handler);
  	django.jQuery("#refresh_connection").click(function() {
  		
  		ddh.getajax('/django_dropbox/get_connection_status/' + obj_id);
  		//alert(test);
  	});
  	
	django.jQuery("#reset_connection").click(function() {
		ddh.getajax('/django_dropbox/reset_connection/' + obj_id);
  		
  	});
      
});



function dropbox_check_connection(){
	return "check was geweldig" 
	
}

function dropbox_reset_connection(){
	return "resetting" 
	
}


function django_dropbox_handler()
{	
	var self = this;
	//print output to this html span
	this.output_span = "#connection_status";
	
	this.write = function(msg,level){
		level = level || "INFO"; //default value for level 		
		//when text is refreshed, remove grayness 
		django.jQuery(this.output_span).removeClass("grayedOut");
		if(level == "ERROR"){			
			django.jQuery(this.output_span).addClass("errors");
		}else{
			django.jQuery(this.output_span).removeClass("errors");
		
		}
		
		django.jQuery(this.output_span).html(msg);	
	}
	
	
	
	this.show_loading = function(){
		django.jQuery(this.output_span).html("loading...");		
	}
	
	this.getajax = function(url){
		//get result from url asynchronously, show loading icon
		this.show_loading();
		
		django.jQuery.ajax({
  			url: url,
  			error: function(xhr, ajaxOptions, thrownError){
      		  					self.write('error: '+xhr.status + xhr.responseText,'ERROR');
    		},
  			success: function(data) {  				
    							self.write(data);
    			
  			}
		});
	
	}
	
} 