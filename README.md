# Fail2Ban Exporter

## Quick Start

```bash
DOCKER_BUILDKIT=1 docker build -t fail2ban-exporter .
docker run -dit --name fail2ban-exporter --user root -v /run/fail2ban/fail2ban.sock:/run/fail2ban/fail2ban.sock fail2ban-exporter
```

## Metrics

```bash
# HELP fail2ban_currently_failed_total Fail2Ban Currently Failed Since Start
# TYPE fail2ban_currently_failed_total counter
fail2ban_currently_failed{jail="authelia",job="fail2ban-exporter"} 0.0
# HELP fail2ban_total_failed_total Fail2Ban Total Failed Since Start
# TYPE fail2ban_total_failed_total counter
fail2ban_total_failed{jail="authelia",job="fail2ban-exporter"} 0.0
# HELP fail2ban_currently_banned_total Fail2Ban Currently Banned
# TYPE fail2ban_currently_banned_total counter
fail2ban_currently_banned{jail="authelia",job="fail2ban-exporter"} 0.0
# HELP fail2ban_total_banned_total Fail2Ban Total Banned
# TYPE fail2ban_total_banned_total counter
fail2ban_total_banned{jail="authelia",job="fail2ban-exporter"} 0.0
# HELP fail2ban_currently_failed_total Fail2Ban Currently Failed Since Start
# TYPE fail2ban_currently_failed_total counter
fail2ban_currently_failed{jail="sshd",job="fail2ban-exporter"} 4.0
# HELP fail2ban_total_failed_total Fail2Ban Total Failed Since Start
# TYPE fail2ban_total_failed_total counter
fail2ban_total_failed{jail="sshd",job="fail2ban-exporter"} 738.0
# HELP fail2ban_currently_banned_total Fail2Ban Currently Banned
# TYPE fail2ban_currently_banned_total counter
fail2ban_currently_banned{jail="sshd",job="fail2ban-exporter"} 1270.0
# HELP fail2ban_total_banned_total Fail2Ban Total Banned
# TYPE fail2ban_total_banned_total counter
fail2ban_total_banned{jail="sshd",job="fail2ban-exporter"} 1333.0
# HELP fail2ban_currently_failed_total Fail2Ban Currently Failed Since Start
# TYPE fail2ban_currently_failed_total counter
fail2ban_currently_failed{jail="traefik",job="fail2ban-exporter"} 60.0
# HELP fail2ban_total_failed_total Fail2Ban Total Failed Since Start
# TYPE fail2ban_total_failed_total counter
fail2ban_total_failed{jail="traefik",job="fail2ban-exporter"} 97.0
# HELP fail2ban_currently_banned_total Fail2Ban Currently Banned
# TYPE fail2ban_currently_banned_total counter
fail2ban_currently_banned{jail="traefik",job="fail2ban-exporter"} 21.0
# HELP fail2ban_total_banned_total Fail2Ban Total Banned
# TYPE fail2ban_total_banned_total counter
fail2ban_total_banned{jail="traefik",job="fail2ban-exporter"} 21.0
```
