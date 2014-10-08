""" Utility functions for working with django Querysets """


def index(queryset,object):
    """Give the zero-based index of first occurrence of object in queryset. 
    Return -1 if not found
    
    """
    
    for index,item in enumerate(queryset):
    	if item == object:
    		return index
    		
    return -1
    
