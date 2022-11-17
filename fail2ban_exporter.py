#!/usr/bin/env python3
#coding: utf-8

'''Fail2Ban Exporter'''

import logging
import os
import sys
import time
from datetime import datetime
from pytz import timezone
from prometheus_client.core import REGISTRY, Metric
from prometheus_client import start_http_server, PROCESS_COLLECTOR, PLATFORM_COLLECTOR
from fail2ban.client.csocket import CSocket

FAIL2BAN_EXPORTER_SOCKET = os.environ.get('FAI2BAN_EXPORTER_SOCKET', '/run/fail2ban/fail2ban.sock')
FAIL2BAN_EXPORTER_NAME = os.environ.get('FAIL2BAN_EXPORTER_NAME',
                                        'fail2ban-exporter')
FAIL2BAN_EXPORTER_LOGLEVEL = os.environ.get('FAIL2BAN_EXPORTER_LOGLEVEL',
                                            'INFO').upper()
FAIL2BAN_EXPORTER_TIMEZONE = os.environ.get('FAIL2BAN_EXPORTER_TIMEZONE',
                                            'Europe/Paris')
# Logging Configuration
logging.Formatter.converter = lambda *args: datetime.now(tz=timezone(FAIL2BAN_EXPORTER_TIMEZONE)).timetuple()
try:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level=FAIL2BAN_EXPORTER_LOGLEVEL)
except ValueError:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level='INFO')
    logging.error("FAIL2BAN_EXPORTER_LOGLEVEL invalid !")
    os._exit(1)

# Check FAIL2BAN_EXPORTER_PORT
try:
    FAIL2BAN_EXPORTER_PORT = int(os.environ.get('FAIL2BAN_EXPORTER_PORT', '8123'))
except ValueError:
    logging.error("FAIL2BAN_EXPORTER_PORT must be int !")
    os._exit(1)

METRICS = [
    {'name': 'currently_failed',
     'description': 'Fail2Ban Currently Failed Since Start',
     'type': 'counter'},
    {'name': 'total_failed',
     'description': 'Fail2Ban Total Failed Since Start',
     'type': 'counter'},
    {'name': 'currently_banned',
     'description': 'Fail2Ban Currently Banned',
     'type': 'counter'},
    {'name': 'total_banned',
     'description': 'Fail2Ban Total Banned',
     'type': 'counter'}
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

class Fail2BanCollector:
    '''Fail2Ban Collector Class'''
    def __init__(self):
        self.fail2ban_socket = None

    def get_jails(self):
        '''Get Fail2Ban Jails'''
        return self.fail2ban_socket.send(["status"])[1][1][1].split(', ')

    def get_jail_stats(self, jail):
        '''Get Fail2Ban Jail Statistics'''
        stats = self.fail2ban_socket.send(["status", jail])
        currently_failed = stats[1][0][1][0][1]
        total_failed = stats[1][0][1][1][1]
        currently_banned = stats[1][1][1][0][1]
        total_banned = stats[1][1][1][1][1]
        return {'currently_failed': currently_failed,
                'total_failed': total_failed,
                'currently_banned': currently_banned,
                'total_banned': total_banned}

    def get_metrics(self):
        '''Get Prometheus Metrics'''
        metrics = []
        jails = self.get_jails()
        if len(jails) == 0:
            self.healthcheck = False
            logging.info("No Fail2Ban Jails, Exiting ...")
            os._exit(1)
        logging.info("Jails : %s", jails)
        for jail in jails:
            labels = {'job': FAIL2BAN_EXPORTER_NAME, 'jail': jail}
            jail_stats = self.get_jail_stats(jail)
            for key, value in jail_stats.items():
                description = [i['description'] for i in METRICS if key == i['name']][0]
                metric_type = [i['type'] for i in METRICS if key == i['name']][0]
                metrics.append({'name': f"fail2ban_{key.lower()}",
                                'value': float(value),
                                'description': description,
                                'type': metric_type,
                                'labels': labels
                              })
        logging.info("Metrics : %s", metrics)
        return metrics

    def collect(self):
        '''Collect Prometheus Metrics'''
        try:
            self.fail2ban_socket = CSocket(FAIL2BAN_EXPORTER_SOCKET)
            metrics = self.get_metrics()
            for metric in metrics:
                prometheus_metric = Metric(metric['name'], metric['description'], metric['type'])
                prometheus_metric.add_sample(metric['name'],
                                             value=metric['value'],
                                             labels=metric['labels'])
                yield prometheus_metric
        except ConnectionRefusedError as exception:
            logging.critical("%s : %s", exception, FAIL2BAN_EXPORTER_SOCKET)
            os._exit(1)
        except FileNotFoundError as exception:
            logging.critical("%s : %s", exception, FAIL2BAN_EXPORTER_SOCKET)
            os._exit(1)
        except PermissionError as exception:
            logging.critical("%s : %s", exception, FAIL2BAN_EXPORTER_SOCKET)
            os._exit(1)

def main():
    '''Main Function'''
    logging.info("Starting Fail2Ban Exporter on port %s.", FAIL2BAN_EXPORTER_PORT)
    logging.debug("FAIL2BAN_EXPORTER_PORT: %s.", FAIL2BAN_EXPORTER_PORT)
    logging.debug("FAIL2BAN_EXPORTER_NAME: %s.", FAIL2BAN_EXPORTER_NAME)
    # Start Prometheus HTTP Server
    start_http_server(FAIL2BAN_EXPORTER_PORT)
    # Init Fail2BanCollector
    REGISTRY.register(Fail2BanCollector())
    # Infinite Loop
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
