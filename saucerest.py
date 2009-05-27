#! /usr/bin/python
import sys
import time
import httplib2
import urllib
import simplejson  # http://cheeseshop.python.org/pypi/simplejson

class SauceClient:
    """Basic wrapper class for operations with Sauce"""

    def __init__(self, name=None, access_key=None):
        self.baseUrl = "https://saucelabs.com"
        self.http = httplib2.Http()
        self.account_name = name
        self.http.add_credentials(name, access_key)

        # Used for job/batch waiting
        self.SLEEP_INTERVAL = 5   # in seconds
        self.TIMEOUT = 300  # TIMEOUT / 60 = number of minutes before timing out

    def get(self, type, doc_id, **kwargs):
        headers = {"Content-Type": "application/json"}
        attachment = ""
        if kwargs.has_key('attachment'):
            attachment = "/%s" % kwargs.pop('attachment')
        if kwargs:
            parameters = "?%s" % (urllib.urlencode(kwargs))
        else:
            parameters = ""
        url = self.baseUrl + "/rest/%s/%s/%s%s%s" % (self.account_name, type, doc_id, attachment, parameters)
        response, content = self.http.request(url, 'GET', headers=headers)
        if attachment:
            return content
        else:
            return simplejson.loads(content)

    def list(self, type):
        headers = {"Content-Type": "application/json"}
        url = self.baseUrl + "/rest/%s/%s" % (self.account_name, type)
        response, content = self.http.request(url, 'GET', headers=headers)
        if attachment:
            return content
        else:
            return simplejson.loads(content)

    def create(self, type, body):
        headers = {"Content-Type": "application/json"}
        url = self.baseUrl + "/rest/%s/%s" % (self.account_name, type)
        body = simplejson.dumps(body)
        response, content = self.http.request(url, 'POST', body=body, headers=headers)
        return simplejson.loads(content)

    def attach(self, doc_id, name, body):
        url = self.baseUrl + "/rest/%s/scripts/%s/%s" % (self.account_name, doc_id, name)
        response, content = self.http.request(url, 'PUT', body=body)
        return simplejson.loads(content)

    def delete(self, type, doc_id):
        headers = {"Content-Type": "application/json"}
        url = self.baseUrl + "/rest/%s/%s/%s" % (self.account_name, type, doc_id)
        response, content = self.http.request(url, 'DELETE', headers=headers)
        return simplejson.loads(content)

    #------ Sauce-specific objects ------

    # Scripts
    def create_script(self, body):
        return self.create('scripts', body)

    def get_script(self, script_id):
        return self.get('scripts', doc_id=script_id)


    # Jobs
    def create_job(self, body):
        return self.create('jobs', body)

    def get_job(self, job_id):
        return self.get('jobs', job_id)

    def list_jobs(self):
        return self.list('jobs')

    def wait_for_jobs(self, batch_id):
        t = 0
        while t < self.TIMEOUT:
            jobs = self.get_jobs(batch=batch_id)
            total_complete = len( [job['Status'] for job in jobs if job['Status'] == 'complete'] )
            total_error = len( [job['Status'] for job in jobs if job['Status'] == 'error'] )

            if total_complete + total_error == len(jobs):
                return

            time.sleep(self.SLEEP_INTERVAL)
            t += self.SLEEP_INTERVAL

        if t >= self.TIMEOUT:
           raise Exception("Timed out waiting for all jobs to finish")

    # Tunnels
    def create_tunnel(self, body):
        return self.create('tunnels', body)

    def get_tunnel(self, tunnel_id):
        return self.get('tunnels', tunnel_id)

    def list_tunnels(self):
        return self.list('tunnels')

    def delete_tunnel(self, tunnel_id):
        return self.delete('tunnels', tunnel_id)
