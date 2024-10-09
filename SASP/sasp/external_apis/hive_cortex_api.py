class HiveAPI:
    def __new__(cls):
        """Override __new__ to make this a singleton class"""
        if not hasattr(cls, 'instance'):
            cls.instance = super(HiveAPI, cls).__new__(cls)
        return cls.instance
    
    def __init__(self, *args, **kwargs):
        # Hive and Cortex are not part of the Open Source version of SASP
        self.logged_in = False

    def get_analyzers(self, pythonify=False):
        """Returns a list of analyzers that are available to run on TheHive

        Args:
            pythonify (bool, optional): Return the data from the request as a python object. Defaults to False.
        """
        pass
    
    def get_open_cases(self, pythonify=False):
        pass
        
    def get_case(self, case_id, cortex4py_object=False):
        """Override of cortex4py's get_case function. Can use vanilla behavior or returns a Case object
        """
        pass
    
    def get_case_fields(self,case_id, pythonify=False):
        """Returns a dictionary of case fields for the given case_id

        Args:
            case_id (str): The case ID to get the fields for
            pythonify (bool, optional): Return the data from the request as a python object. Defaults to False.
        """
        pass
    
    def run_analyzer(self, case_id, artifact_id, analyzer_id, pythonify=False):
        pass
    
    def get_case_observables(self, case_id,filter=None, pythonify=False):
        """Returns a list of observables for the given case_id

        Args:
            case_id (str): The case ID to get the observables for
            filter (dict, optional): A list of filters to apply to the request in an AND fashion. Must contain only hive4py.query.Query objects. Defaults to None.
            pythonify (bool, optional): Return the data from the request as a python object. Defaults to False.
        """
        pass
    
    def get_observable_by_case_and_artifact(self, case_id, artifact_label, pythonify=False):
        """Uses get_case_observables to find the observable from the given case_id and artifact_label

        Args:
            case_id (str): The case ID to get the observables for e.g. ~4160
            artifact_label (str): A single artifact label to filter the observables by e.g. 'File' or 'auto_label_customname'
            pythonify (bool, optional): Return as a python dictionary, rather than request object. Defaults to False.
        """
        pass
    
    def get_observable_jobs(self,observable_id, pythonify=False):
        """Returns a list of jobs that have been run on the given observable_id
        """
        pass
        
    def get_case_analyzer_result(self, case_id, analyzer_idOrName, observable_idOrName, pythonify=False):
        """Returns the result of the analyzer run on the given observable
        """
        pass
    
class CortexApi:
    # Because CortexApi takes non-keyword arguments, we can't use this singleton pattern
    # alternatives might exist, but for now it being a non-singleton is fine
    # If needed later, refer to https://stackoverflow.com/questions/51896862
    def __new__(cls):
        """Override __new__ to make this a singleton class"""
        if not hasattr(cls, 'instance'):
            cls.instance = super(CortexApi, cls).__new__(cls)
        return cls.instance
    
    def __init__(self, *args, **kwargs):
        # Hive and Cortex are not part of the Open Source version of SASP
        self.logged_in = False

    
    def get_jobs_for_artifact(self, artifact_id):
        """Returns a list of jobs that have been run on the given artifact_id
        """
        pass
    
    def get_responders(self, pythonify=False):
        """Returns a list of responders that are available to run on Cortex
        """
        pass
    
    def run_responder(self, data, responder_id=None, responder_name=None):
        """Runs the responder with the given responder_id or responder_name on the given data
        """
        pass