#!/usr/bin/env python3

import requests
import sys
import time
import json
import urllib
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from bs4 import BeautifulSoup

SERVE_HOST = '0.0.0.0'
SERVE_PORT = 8000
PREDISTRIBUCE_URL = 'https://www.predistribuce.cz/com/PREdi/UI/Forms/Hdo/HdoForm:hdoOneDayAjax'

def get_hdo_html(date, povel):
    response = requests.post(PREDISTRIBUCE_URL, data={"datum": date, "povel": povel})

    if response.status_code != 200:
        raise RuntimeError('Website predistribuce.cz is unreachable.')

    return response.json()['html']

def parse_hdo_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    timeline = []
    lastItemTariff = None
    for item in soup.find_all('span'):
        if item['class'] == ['span-overflow']:
            if lastItemTariff is None:
                raise RuntimeError('Error while parsing data from predistribuce.cz')

            times = item['title'].split(' - ')
            timeline.append({
                'begin': datetime.strptime(times[0],"%H:%M").time(),
                'end': datetime.strptime(times[1],"%H:%M").time(), 
                'tariff': lastItemTariff
            })
        elif item['class'] == ['hdont']:
            lastItemTariff = 'low'
        elif item['class'] == ['hdovt']:
            lastItemTariff = 'high'

    nowTime = datetime.now().time()
    for idx, item in enumerate(timeline):
        if nowTime >= item['begin'] and nowTime <= item['end']:
            return {
                'current': item,
                'next': timeline[(idx + 1) % len(timeline)],
                'timeline': timeline
            }
        
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsedurl = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsedurl.query)
        
        if not 'povel' in query:
            raise RuntimeError('Povel not specified')

        povel = query['povel'][0]

        today = time.strftime("%d.%m.%Y")
        hdo_data = parse_hdo_data(get_hdo_html(today, povel))

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        self.wfile.write(json.dumps(hdo_data, default=str).encode('utf8'))
        return