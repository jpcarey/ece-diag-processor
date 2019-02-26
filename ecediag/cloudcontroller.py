from cursesmenu import CursesMenu, SelectionMenu
from distutils.version import StrictVersion
import requests
import getpass
import base64
import json
import time
import sys
import os


from ecediag.basicconfig import config
from ecediag import securesettings

TRACE = False
CLUSTER_NAME = 'support-ece-diagnostic'
cloud = lambda c: 'https://cloud.elastic.co/' + c.strip("/")


def createCloud():
    s = requests.Session()

    loginCloud(s)
    cluster_name, cluster_id = clusterCheck(s)

    if not cluster_name:
        # print("CLUSTER NOT FOUND")

        regions = s.get(cloud('/api/v0/regions'))
        writeJson('regions.json', regions.json())

        ### PROMPT for REGION ###
        regionId = promptForRegion(regions.json())

        v0region = '/api/v0/v1-regions/{}'.format(regionId)

        versions = s.get(cloud("{}/stack/versions".format(v0region)))
        writeJson('versions.json', versions.json())

        version = findLatestVersion(versions.json()["stacks"])

        template_api = '{}/platform/configuration/templates/deployments{}'.format(
            v0region,
            '?stack_version={}'.format(version[0])
        )
        templates = s.get(cloud(template_api))
        writeJson('templates.json', templates.json())

        templateID = templates.json()[0]["id"]

        ct = templates.json()[0]["cluster_template"]
        ct["apm"]["plan"]["apm"]["version"] = version[0]
        ct["kibana"]["plan"]["kibana"]["version"] = version[0]
        ct["plan"]["elasticsearch"]["version"] = version[0]
        ct["cluster_name"] = CLUSTER_NAME
        ct["plan"]["deployment_template"] = {"id": templateID}
        ct["plan"]["transient"] = dict()

        create_api = '{}/clusters/elasticsearch?validate_only=false'.format(
            v0region
        )
        create = s.post(cloud(create_api), json=ct)
        writeJson('create.json', create.json())

        credentials = create.json()["credentials"]
        es_cluster_id = create.json()["elasticsearch_cluster_id"]

        status_opts = [
            "show_security=true",
            "show_metadata=true",
            "show_plans=true",
            "show_plan_logs=true",
            "show_plan_defaults=true",
            "convert_legacy_plans=true",
            "show_system_alerts=3",
            "show_settings=true",
            "enrich_with_template=true"
        ]

        status_api = '{}/clusters/elasticsearch/{}?{}'.format(
            v0region,
            es_cluster_id,
            '&'.join(status_opts)
        )
        status = s.get(cloud(status_api))
        writeJson('status.json', status.json())

        base,elasticsearch,kibana = base64.b64decode(
            status.json()["metadata"]["cloud_id"].split(":")[1]
            ).decode('utf-8').split("$")

        es_url = 'https://{}.{}:9243'.format(elasticsearch, base)
        kb_url = 'https://{}.{}:9243'.format(kibana, base)

        print("✔ Created Cloud Cluster ({}): {}".format(version[0], es_cluster_id))
        print("\telasticsearch: {}".format(es_url))
        print("\tkibana: {}".format(kb_url))
        print("\tes_user: {}".format(credentials["username"]))
        print("\tes_pass: {}".format(credentials["password"]))


        print("✔ Creating keystore")
        securesettings.addKeystoreItem("ES_URL", es_url)
        securesettings.addKeystoreItem("ES_USER", credentials["username"])
        securesettings.addKeystoreItem("ES_PASS", credentials["password"])
        securesettings.addKeystoreItem("KB_URL", kb_url)

        checkCreationStatus(s, v0region, es_cluster_id)

    else:
        print("✔ Cloud Cluster: {}, {}".format(cluster_name, cluster_id))
        securesettings.load()


def checkCreationStatus(s, v0region, es_cluster_id):
    for i in range(24):
        status_api = '{}/clusters/elasticsearch/{}?show_plan_logs=true'.format(
            v0region,
            es_cluster_id
        )
        status = s.get(cloud(status_api))
        writeJson("CreateStatus.json", status.json())
        if status.json()["status"] == "started":
            sys.stdout.write('\r✔ Cluster is online\n')
            sys.stdout.flush()
            return
        else:
            steps = status.json()["plan_info"]["pending"]["plan_attempt_log"]
            try:
                r = next(step for step in steps if step["stage"] != "completed")
                spinner = spinning_cursor()
                for _ in range(150):
                    sys.stdout.write('\r{} {}'.format(
                        r["step_id"], next(spinner)))
                    sys.stdout.flush()
                    time.sleep(0.1)
                    sys.stdout.write('\b')
            except StopIteration:
                # This really shouldn't happen...
                pass
    sys.exit("Something went wrong. Waited 6 minutes for the cluster to start")


def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor


def clusterCheck(s):
    clusters = s.post(cloud('/api/v0/v1-regions/clusters/elasticsearch/_search'))
    writeJson('clusters_search.json', clusters.json())

    cd = clusters.json()
    try:
        return next((c['cluster_name'],c['cluster_id']) for c in
            cd['elasticsearch_clusters'] if c['cluster_name'] == CLUSTER_NAME)
    except StopIteration:
        return (None, None)


def loginCloud(s):
    print("Enter Elastic Cloud credentials")
    username = config.get('ECE_DIAG', 'CloudUser')
    lines = 0
    if username != "":
        user_out = "Username: {} (loaded from settings.ini CloudUser)".format(
                        username)
        print(user_out)
        lines += 2
    else:
        print("Tip: set your username in the settings.ini CloudUser")
        username = input('Enter your username: ')
        user_out = "Username: {}".format(username)
        lines += 2

    password = getpass.getpass("Password: ")
    body = {"email":username,"password":password}

    login = s.post(cloud('/api/v1/users/_login'), json=body)
    if login.status_code == requests.codes.ok:
        writeJson('_login.json', login.json())

        # add return cookie to any further requests within this session
        cookie = login.json()['token']
        s.headers.update({'Authorization': 'Bearer {}'.format(cookie)})

        for _ in range(lines):
            sys.stdout.write("\033[F") #back to previous line
            sys.stdout.write("\033[K") #clear line

        print('✔ {}'.format(user_out))
        print("✔ Password")

    else:
        print("[{}] {} http response code, {}".format(
            login.status_code,
            login.reason,
            login.text
            ))
        sys.exit("login failed. exiting")


def promptForRegion(regionData):
    regionNames = [region["data"]["name"] for region in regionData["regions"]]
    title = "Creating a new cluster. Select your Elastic Cloud region"
    selection = SelectionMenu.get_selection(regionNames, title=title)
    if selection > (len(regionNames) - 1):
        sys.exit("Canceled region selection")
    else:
        selectedRegion = regionData["regions"][selection]
        # print(selectedRegion)
        return selectedRegion["identifier"]


def writeJson(filename, data):
    if TRACE:
        filename = os.path.join(
            config.get("PATHS", "script_dir"),
            'tmp',
            filename
            )
        with open(filename, 'w') as outfile:
            json.dump(data, outfile, sort_keys=True,
                        indent=4, separators=(',',': '))


def findLatestVersion(data):
    version = (None, None)
    for i,v in enumerate(data):
        if version[0] == None:
            version = (v["version"], i)
        else:
            if StrictVersion(v["version"]) > StrictVersion(version[0]):
                version = (v["version"], i)
            else:
                pass
    return version
