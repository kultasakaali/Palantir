import maxminddb
import os

# cron job:
# update GeoLite2-Country.mmdb on every Monday 03:33
# 33 3 * * 1 bash -c 'mkdir -p ~/.geoip/ && curl -L https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb > ~/.geoip/GeoLite2-Country.mmdb'

class GeoIpHelperException(Exception):
    pass

SEARCH_PATHS = [
    '$GEOIP_PATH',
    '~/.geoip',
    '/usr/share/GeoIP',
    '/var/lib/GeoIP'
]

def expand_path(path):
    vars_expanded = os.path.expandvars(path)
    return os.path.expanduser(vars_expanded)

def find_country_mmdb():
    filename = 'GeoLite2-Country.mmdb'
    for search_path in SEARCH_PATHS:
        fullpath = os.path.join(expand_path(search_path), filename)
        if os.path.exists(fullpath):
            return fullpath
    raise GeoIpHelperException(f"Could not find {filename} at: {SEARCH_PATHS}")

def query_geoip(ip):
    geoip_filename = find_country_mmdb()
    with maxminddb.open_database(geoip_filename) as db:
        return db.get(ip)["country"]["iso_code"]
