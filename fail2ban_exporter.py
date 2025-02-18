#!/usr/bin/env python3
# coding: utf-8
# pyright: reportMissingImports=false, reportOptionalMemberAccess=false

"""Fail2Ban Exporter"""

import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable
from wsgiref.simple_server import make_server

import pytz
from fail2ban.client.csocket import CSocket
from prometheus_client import PLATFORM_COLLECTOR, PROCESS_COLLECTOR
from prometheus_client.core import REGISTRY, CollectorRegistry, Metric
from prometheus_client.exposition import _bake_output, _SilentHandler, parse_qs

FAIL2BAN_EXPORTER_SOCKET = os.environ.get(
    "FAIL2BAN_EXPORTER_SOCKET", "/run/fail2ban/fail2ban.sock"
)
FAIL2BAN_EXPORTER_NAME = os.environ.get("FAIL2BAN_EXPORTER_NAME", "fail2ban-exporter")
FAIL2BAN_EXPORTER_LOGLEVEL = os.environ.get(
    "FAIL2BAN_EXPORTER_LOGLEVEL", "INFO"
).upper()
FAIL2BAN_EXPORTER_TZ = os.environ.get("TZ", "Europe/Paris")


def make_wsgi_app(
    registry: CollectorRegistry = REGISTRY, disable_compression: bool = False
) -> Callable:
    """Create a WSGI app which serves the metrics from a registry."""

    def prometheus_app(environ, start_response):
        # Prepare parameters
        accept_header = environ.get("HTTP_ACCEPT")
        accept_encoding_header = environ.get("HTTP_ACCEPT_ENCODING")
        params = parse_qs(environ.get("QUERY_STRING", ""))
        headers = [
            ("Server", ""),
            ("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
            ("X-Content-Type-Options", "nosniff"),
            ("Cross-Origin-Resource-Policy", "same-origin"),
            ("Cross-Origin-Embedder-Policy", "require-corp"),
            ("Cross-Origin-Opener-Policy", "same-site"),
        ]
        if environ["PATH_INFO"] == "/":
            status = "301 Moved Permanently"
            headers.append(("Location", "/metrics"))
            output = b""
        elif environ["PATH_INFO"] == "/favicon.ico":
            status = "200 OK"
            output = b""
        elif environ["PATH_INFO"] == "/metrics":
            status, tmp_headers, output = _bake_output(
                registry,
                accept_header,
                accept_encoding_header,
                params,
                disable_compression,
            )
            headers += tmp_headers
        else:
            status = "404 Not Found"
            output = b""
        start_response(status, headers)
        return [output]

    return prometheus_app


def start_wsgi_server(
    port: int,
    addr: str = "0.0.0.0",  # nosec B104
    registry: CollectorRegistry = REGISTRY,
) -> None:
    """Starts a WSGI server for prometheus metrics as a daemon thread."""
    app = make_wsgi_app(registry)
    httpd = make_server(addr, port, app, handler_class=_SilentHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()


start_http_server = start_wsgi_server

# Logging Configuration
try:
    pytz.timezone(FAIL2BAN_EXPORTER_TZ)
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone(FAIL2BAN_EXPORTER_TZ)
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level=FAIL2BAN_EXPORTER_LOGLEVEL,
    )
except pytz.exceptions.UnknownTimeZoneError:
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone("Europe/Paris")
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("TZ invalid ! : %s", FAIL2BAN_EXPORTER_TZ)
    os._exit(1)
except ValueError:
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("FAIL2BAN_EXPORTER_LOGLEVEL invalid !")
    os._exit(1)

# Check FAIL2BAN_EXPORTER_PORT
try:
    FAIL2BAN_EXPORTER_PORT = int(os.environ.get("FAIL2BAN_EXPORTER_PORT", "8123"))
except ValueError:
    logging.error("FAIL2BAN_EXPORTER_PORT must be int !")
    os._exit(1)

METRICS = [
    {
        "name": "currently_failed",
        "description": "Fail2Ban Currently Failed Since Start",
        "type": "counter",
    },
    {
        "name": "total_failed",
        "description": "Fail2Ban Total Failed Since Start",
        "type": "counter",
    },
    {
        "name": "currently_banned",
        "description": "Fail2Ban Currently Banned",
        "type": "counter",
    },
    {
        "name": "total_banned",
        "description": "Fail2Ban Total Banned",
        "type": "counter",
    },
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors["python_gc_objects_collected_total"])


class Fail2BanCollector:
    """Fail2Ban Collector Class"""

    def __init__(self):
        self.fail2ban_socket = None

    def get_jails(self):
        """Get Fail2Ban Jails"""
        return self.fail2ban_socket.send(["status"])[1][1][1].split(", ")

    def get_jail_stats(self, jail):
        """Get Fail2Ban Jail Statistics"""
        stats = self.fail2ban_socket.send(["status", jail])
        currently_failed = stats[1][0][1][0][1]
        total_failed = stats[1][0][1][1][1]
        currently_banned = stats[1][1][1][0][1]
        total_banned = stats[1][1][1][1][1]
        return {
            "currently_failed": currently_failed,
            "total_failed": total_failed,
            "currently_banned": currently_banned,
            "total_banned": total_banned,
        }

    def get_metrics(self):
        """Get Prometheus Metrics"""
        metrics = []
        jails = self.get_jails()
        if len(jails) == 0:
            logging.info("No Fail2Ban Jails, Exiting ...")
            os._exit(1)
        logging.info("Jails : %s", jails)
        for jail in jails:
            labels = {"job": FAIL2BAN_EXPORTER_NAME, "jail": jail}
            jail_stats = self.get_jail_stats(jail)
            for key, value in jail_stats.items():
                description = [i["description"] for i in METRICS if key == i["name"]][0]
                metric_type = [i["type"] for i in METRICS if key == i["name"]][0]
                metrics.append(
                    {
                        "name": f"fail2ban_{key.lower()}",
                        "value": float(value),
                        "description": description,
                        "type": metric_type,
                        "labels": labels,
                    }
                )
        logging.info("Metrics : %s", metrics)
        return metrics

    def collect(self):
        """Collect Prometheus Metrics"""
        try:
            self.fail2ban_socket = CSocket(FAIL2BAN_EXPORTER_SOCKET)
            metrics = self.get_metrics()
            for metric in metrics:
                prometheus_metric = Metric(
                    metric["name"], metric["description"], metric["type"]
                )
                prometheus_metric.add_sample(
                    metric["name"], value=metric["value"], labels=metric["labels"]
                )
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
    """Main Function"""
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


if __name__ == "__main__":
    main()
