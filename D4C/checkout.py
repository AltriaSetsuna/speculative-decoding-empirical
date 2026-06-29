"""
DATA PROCESS SCRIPTS
FOR DEFECTS4J V2.0
"""
import argparse
import csv
import os
import shutil
import subprocess

def checkout_slug(repos_dir, project, bug_id):
    unique_id = project + '_' + str(bug_id)
    work_dir = os.path.join(repos_dir, unique_id + '_buggy')
    try:
        if os.path.isdir(work_dir) and os.listdir(work_dir):
            print("skip existing: " + unique_id)
            return
        if os.path.isdir(work_dir):
            shutil.rmtree(work_dir)
        print("in processing: " + unique_id)
        cmd = ['defects4j', 'checkout', '-p', project, '-v', str(bug_id) + 'b', '-w', work_dir]
        subprocess.run(cmd, check=True)
    except (RuntimeError, TypeError, NameError, FileNotFoundError) as e:
        print(e)
    except subprocess.CalledProcessError as e:
        print(e)


def get_repos(root_dir, proj_list, id_list):

    repos_dir = root_dir + 'defects4j/'
    os.makedirs(repos_dir, exist_ok=True)
    for i in range(len(proj_list)):
        project = proj_list[i]
        for j in id_list[i]:
            checkout_slug(repos_dir, project, j)


def get_data_repos(root_dir, data_path):
    repos_dir = root_dir + 'defects4j/'
    os.makedirs(repos_dir, exist_ok=True)
    counts = {}
    with open(data_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            slug = row['slug']
            counts[slug] = counts.get(slug, 0) + 1
    slugs = sorted(slug for slug, count in counts.items() if count == 1)
    for slug in slugs:
        project, bug_id = slug.rsplit('_', 1)
        checkout_slug(repos_dir, project, bug_id)
                
parser = argparse.ArgumentParser()
parser.add_argument('--all', action='store_true', help='checkout every Defects4J bug range used by D4C')
parser.add_argument('--data-path', default='data/defects4j_code.csv')
args = parser.parse_args()

root_dir = os.getcwd() + '/'
proj_list = [
            'Chart',
            'Math',
            'Lang',
            'Cli',
            'Closure',
            'Codec',
            'Mockito',
            'Jsoup',
            'JacksonDatabind',
            'JacksonCore',
            'Compress',
            'Collections',
            'Time',
            'JacksonXml',
            'Gson',
            'Csv',
            'JxPath'
            ]   
id_range = [
            '1-25',
            '1-105',
            '1-64',
            '2-40',
            '1-170',
            '2-18',
            '1-37',
            '2-93',
            '2-112',
            '2-26',
            '2-47',
            '26-28',
            '1-27',
            '2-6',
            '2-18',
            '2-16',
            '2-22',
            ]
id_list = []
for i in range(len(id_range)):
    rangeStart = id_range[i].split('-')[0]
    rangeEnd = id_range[i].split('-')[1]
    id_list.append(range(int(rangeStart), int(rangeEnd)+1))
    
if args.all:
    get_repos(root_dir, proj_list, id_list)
else:
    get_data_repos(root_dir, args.data_path)
    
