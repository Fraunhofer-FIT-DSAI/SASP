from django.template.defaultfilters import register

@register.filter(name='dict_key')
def dict_key(dict_, key):    
    return dict_.get(key)