from thehive4py import TheHiveApi
from thehive4py.errors import TheHiveError

from django.contrib.auth.models import User
import requests
import threading

from logging import getLogger

class Hive:
    _user_dict = dict()
    _lock = threading.RLock()
    
    @classmethod
    def HiveAPI(cls, user) -> 'HiveAPI':
        with cls._lock:
            if isinstance(user, User):
                user_name = user.username
            else:
                user_name = user
            if User.objects.filter(username=user_name).first().profile.logins.filter(name='hive').first().connected:
                if user_name in cls._user_dict:
                    return cls._user_dict[user_name]
                else:
                    cls.update_user(user_name)
                    return cls._user_dict[user_name]
            else:
                return None
    
    @classmethod
    def update_user(cls, user: str | User):
        with cls._lock:
            if isinstance(user, User):
                user_profile = user.profile
                user_name = user.username
            else:
                user_profile = User.objects.get(username=user).profile
                user_name = user
            
            config = user_profile.logins.get(name='hive')
            hive = HiveAPI(url=config.url, apikey=config.token)
            hive = hive if hive.logged_in else None
            cls._user_dict[user_name] = hive
        return hive.logged_in if hive else False

class HiveAPI(TheHiveApi):
    def __init__(self, *args, cortex_id='local', **kwargs):
        super().__init__(*args, **kwargs)
        self.cortex_id = cortex_id
        self.logger = getLogger(__name__)
        self.url = self.session.hive_url

        try:
            _ = self.user.get_current()
            self.logged_in = True
        except (
            TheHiveError,
            requests.exceptions.RequestException,
            ) as e:
            self.logged_in = False
            self.logger.error("Failed to login to TheHive: {}".format(e))

    def get_analyzers(self):
        """Returns a list of analyzers that are available to run on TheHive
        """
        return self.cortex.list_analyzers()
    
    def get_open_cases(self):
        response = self.case.find(
            filters={"_and": [{"_field": "status", "_value": "Open"}]}
        )
        return response
        
    def get_case(self, case_id) -> dict:
        """Returns a dictionary containing case information

        Args:
            case_id (str): The ID of the case e.g. ~8630

        Returns:
            dict: Dictionary containing case information
        """
        return self.case.get(case_id=case_id)
    
    def run_analyzer(self, artifact_id, analyzer_id):
        """Run analyzer by artifact and analyzer id.

        Args:
            artifact_id (str): e.g. ~40964256
            analyzer_id (str): e.g. VirusTotal_GetReport_3_1
        """
        return self.cortex.create_analyzer_job(
            {
                "analyzerId": analyzer_id,
                'cortexId': self.cortex_id,
                "artifactId": artifact_id,
            }
        )
    
    def get_analyzer_job(self, job_id) -> dict:
        """Return information about the job with the given id

        Args:
            job_id (str): e.g. ~81924168

        Returns:
            dict: A dictionary containing information about the job
        """
        return self.cortex.get_analyzer_job(job_id=job_id)
    
    def get_responder_job(self, job_id:str, case_id:str=None, case_name:str=None) -> dict:
        """Return information about the job with the given id

        Args:
            job_id (str): The cortexJobId of the job to get information for e.g. kd78aIkBzDx3kdZvsEfT
            case_id (str, optional): The case ID to get the job for e.g. ~8630. Either case_id or case_name must be provided. Defaults to None.
            case_name (_type_, optional): The case name to get the job for e.g. 'My Case'. Either case_id or case_name must be provided. Defaults to None.

        Returns:
            dict: A dictionary containing information about the job
        """
        idOrName = case_id or case_name
        response = self.query.run([
            {
                '_name': 'getCase',
                'idOrName': idOrName
            },
            {
                '_name': 'actions',
            },
        ])
        
        for action in response: 
            if action.get('cortexJobId') == job_id:
                return action
        raise ValueError(f"No job found for case '{idOrName}' with id '{job_id}'")
    
    def get_case_observables(self, case_id):
        """Returns a list of observables for the given case_id

        Args:
            case_id (str): The case ID to get the observables for e.g. ~8630
        """
    
        return self.case.find_observables(case_id=case_id)
    
    def get_observable_by_case_and_artifact(self, case_id, artifact_label):
        """Uses get_case_observables to find the observable from the given case_id and artifact_label

        Args:
            case_id (str): The case ID to get the observables for e.g. ~4160
            artifact_label (str): A single artifact label to filter the observables by e.g. 'File' or 'auto_label_customname'
        """
        return [
            observable 
            for observable in self.get_case_observables(case_id)
            if artifact_label in observable.get('tags',[])
        ]

    
    def get_observable_jobs(self,observable_id):
        """Returns a list of jobs that have been run on the given observable_id
        """
        return self.query.run(
            [
                {"_name":"getObservable","idOrName":observable_id},
                {"_name":"jobs"},
                {"_name":"sort","_fields":[{"startDate":"desc"}]},
                {"_name":"page","from":0,"to":200}
            ]
        )
        
    def get_case_analyzer_result(self, case_id, analyzer_idOrName, observable_idOrName):
        """Returns the result of the analyzer run on the given observable
        """
        
        case_observables = self.get_case_observables(case_id)
        case_observables = [x for x in case_observables if x['message'] == observable_idOrName or x['_id'] == observable_idOrName]
        if len(case_observables) == 0:
            raise ValueError("No observable found with ID or name: {}".format(observable_idOrName))
        elif len(case_observables) > 1:
            observable_id = sorted(case_observables, key=lambda x: x['_createdAt'], reverse=True)[0]['_id']
        else:
            observable_id = case_observables[0]['_id']

        observable_jobs = self.get_observable_jobs(observable_id)
        for job in observable_jobs:
            if analyzer_idOrName in {job.get('analyzerId'), job.get('analyzerName'), job.get('id')}:
                return job
        raise ValueError("No analyzer found with ID or name: {} for observable: {}".format(analyzer_idOrName, observable_idOrName))

    def get_responders(self, case_id):
        """Returns a list of responders that are available to run on this case
        
        Args:
            case_id(str): The id of the active case e.g. ~8630
        """
        return self.cortex.list_responders(
            entity_type='case',
            entity_id=case_id
        )
    
    def run_responder(self, case_id, responder_idOrName, data):
        """Runs the responder with the given responder_id or responder_name on the given data
        """
        responder_id = None
        for responder in self.get_responders(case_id=case_id):
            if (
                responder.get('id') == responder_idOrName or
                responder.get('name') == responder_idOrName
            ):
                responder_id = responder.get('id')
                break
        if not responder_id:
            raise ValueError(f"No responder found for case '{case_id}' with id or name '{responder_idOrName}'")
        
        return self.cortex.create_responder_action(
            {
                'objectId': case_id,
                'objectType': 'case',
                'responderId': responder_id,
                'parameters': data
            }
        )

