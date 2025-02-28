from locust import HttpUser, TaskSet, task, between
import os,sys
sys.path.append(os.path.join(os.getcwd(), "tests"))
from test_api import get_generic_api_key
import test_set


class UserBehavior(TaskSet):
    @task(2)
    def gene_task(self):
        gene_symbol = test_set.gene_list()
        url = f"gene/{gene_symbol}"
        self.client.get(url)

    @task(1)
    def variant_task(self):
        generic_api_key = get_generic_api_key()
        variant_id = test_set.variant_list_nm()
        url = f"api/variant/create?variant_chgvs={variant_id}&caller=cli&api_key={generic_api_key}"
        self.client.get(url)

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(0.1, 2)  # seconds