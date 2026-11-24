#!/usr/bin/env bash
# Publish the five strategy endpoints on the HOST machine so they are reachable from outside
# (Minikube's docker driver keeps NodePorts on a private network). Uses kubectl port-forward.
#   scripts/expose.sh start     8081 rolling | 8082 blue-green | 8083 canary | 8084 shadow | 8085 A/B
#   scripts/expose.sh stop
set -euo pipefail
PIDFILE=/tmp/aceest-portforward.pids
case "${1:-start}" in
    start)
        : > "$PIDFILE"
        forward() {  # <service> <host port>
            nohup kubectl -n aceest port-forward --address 0.0.0.0 "svc/$1" "$2:80" \
                >"/tmp/pf-$1.log" 2>&1 &
            echo $! >> "$PIDFILE"
        }
        forward aceest-rolling 8081
        forward aceest-bluegreen 8082
        forward aceest-canary 8083
        forward aceest-shadow-router 8084
        forward aceest-ab-router 8085
        sleep 2
        echo "rolling    http://$(hostname -I | awk '{print $1}'):8081"
        echo "blue-green http://$(hostname -I | awk '{print $1}'):8082"
        echo "canary     http://$(hostname -I | awk '{print $1}'):8083"
        echo "shadow     http://$(hostname -I | awk '{print $1}'):8084"
        echo "a/b        http://$(hostname -I | awk '{print $1}'):8085"
        ;;
    stop)
        [ -f "$PIDFILE" ] && xargs -r kill < "$PIDFILE" || true
        rm -f "$PIDFILE"; echo "stopped"
        ;;
    *) echo "usage: $0 start|stop"; exit 1;;
esac
