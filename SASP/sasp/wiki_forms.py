import sasp.models
import sasp.wiki_interface
import logging

from rich import print as rprint

class WikiFormManager:
    logger = logging.getLogger(__name__)
    @classmethod
    def update_wiki(cls, dry_run=False):
        properties = {}
        templates = {}
        for playbook_type in sasp.models.Playbook.__subclasses__():
            try:
                pb_properties = playbook_type.get_properties()
                for prop in pb_properties:
                    if prop['prop'] in properties:
                        if properties[prop['prop']]['type'] != prop['type']:
                            raise KeyError(f"Conflicting prop definition for prop '{prop['prop']}'")
                for prop in pb_properties:
                    properties[prop['prop']] = {'type':prop['type'],'prop':prop['prop']}
            except Exception as e:
                cls.logger.error(f"Error getting properties for {playbook_type.__name__}: {e}")
            try:
                pb_templates = playbook_type.get_templates()
                for key in pb_templates:
                    if key in templates:
                        raise KeyError(f"Template name '{key}' is already defined.")
                templates.update(pb_templates)
            except Exception as e:
                cls.logger.error(f"Error getting templates for {playbook_type.__name__}: {e}")
        
        wiki = sasp.wiki_interface.Wiki()
        for i,prop in enumerate(properties.values()):
            rprint(f'[blue]Writing property "{prop["prop"]}" {i+1}/{len(properties)}:[/blue]')
            cls.write_property(prop, wiki, dry_run=dry_run)
        
        i = 0
        for name, context in templates.items():
            rprint(f'[blue]Writing template "{name}" {i+1}/{len(templates)}:[/blue]')
            i+=1
            cls.write_category(name, context, wiki, dry_run=dry_run)
            cls.write_template(name, context, wiki, dry_run=dry_run)
    
    @classmethod
    def write_property(cls, prop, wiki, dry_run=False):
        wiki.set_page(
            f"Property:{prop['prop']}",
            template_name="wiki_property.jinja",
            context={
                'prop_type': prop['type'],
            },
            dry_run=dry_run
        )
    
    @classmethod
    def write_template(cls, name, context, wiki, dry_run=False):
        wiki.set_page(
            f"Template:{name}",
            template_name="wiki_template.jinja",
            context=context,
            dry_run=dry_run
        )
    
    @classmethod
    def write_category(cls, name, context, wiki, dry_run=False):
        wiki.set_page(
            f"Category:{name}",
            template_name="wiki_category.jinja",
            dry_run=dry_run
        )