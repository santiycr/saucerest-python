#! /usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Sauce Labs Inc
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# 'Software'), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import time
import httplib2
import urllib
import simplejson  # http://cheeseshop.python.org/pypi/simplejson


class SauceClient:
    """Basic wrapper class for operations with Sauce"""

    def __init__(self, name=None, access_key=None,
                 base_url="https://saucelabs.com",
                 timeout=30):
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self.baseUrl = base_url
        self.http = httplib2.Http(timeout=timeout)
        self.account_name = name
        self.http.add_credentials(name, access_key)

        # Used for job/batch waiting
        self.SLEEP_INTERVAL = 5   # in seconds
        self.TIMEOUT = 300  # TIMEOUT/60 = number of minutes before timing out

    def get(self, type, doc_id, **kwargs):
        headers = {"Content-Type": "application/json"}
        attachment = ""
        if 'attachment' in kwargs:
            attachment = "/%s" % kwargs.pop('attachment')
        if kwargs:
            parameters = "?%s" % (urllib.urlencode(kwargs))
        else:
            parameters = ""
        url = self.baseUrl + "/rest/%s/%s/%s%s%s" % (self.account_name,
                                                     type,
                                                     doc_id,
                                                     attachment,
                                                     parameters)
        response, content = self.http.request(url, 'GET', headers=headers)
        if attachment:
            return content
        else:
            return simplejson.loads(content)

    def list(self, type):
        headers = {"Content-Type": "application/json"}
        url = self.baseUrl + "/rest/%s/%s" % (self.account_name, type)
        response, content = self.http.request(url, 'GET', headers=headers)
        return simplejson.loads(content)

    def create(self, type, body):
        headers = {"Content-Type": "application/json"}
        url = self.baseUrl + "/rest/%s/%s" % (self.account_name, type)
        body = simplejson.dumps(body)
        response, content = self.http.request(url,
                                              'POST',
                                              body=body,
                                              headers=headers)
        return simplejson.loads(content)

    def attach(self, doc_id, name, body):
        url = self.baseUrl + "/rest/%s/scripts/%s/%s" % (self.account_name,
                                                         doc_id, name)
        response, content = self.http.request(url, 'PUT', body=body)
        return simplejson.loads(content)

    def delete(self, type, doc_id):
        headers = {"Content-Type": "application/json"}
        url = self.baseUrl + "/rest/%s/%s/%s" % (self.account_name,
                                                 type,
                                                 doc_id)
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
            total_comp = len([j for j in jobs if j['Status'] == 'complete'])
            total_err = len([j for j in jobs if j['Status'] == 'error'])

            if total_comp + total_err == len(jobs):
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
