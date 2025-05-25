#!/bin/bash
# wait-for-it.sh

set -e

host="$1"
shift
cmd="$@"

echo "Waiting for MySQL at $host..."

until mysql -h "$host" -u root -proot -e 'SELECT 1' > /dev/null 2>&1; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "MySQL is up - executing command: $cmd"
exec $cmd 