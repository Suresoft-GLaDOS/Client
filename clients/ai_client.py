import argparse
import os
import json
import requests
import sys
import whatthepatch

from clients.client_interface import ValidatorClient
from git import Repo

VULCAN_OUTPUT_DIR = os.getenv("VULCAN_OUTPUT_DIR", None)
VULCAN_TARGET = os.getenv("VULCAN_TARGET", None)
MSV_PATCH_DIFF_PATH = os.getenv("MSV_PATCH_DIFF_PATH", None)
VALIDATION_REPORT_DIR = os.path.join(VULCAN_OUTPUT_DIR, "validation")


def check_environments():
    print(f"[INFO] VULCAN_OUTPUT_DIR={VULCAN_OUTPUT_DIR}", flush=True)
    print(f"[INFO] VULCAN_TARGET={VULCAN_TARGET}", flush=True)
    print(f"[INFO] MSV_PATCH_DIFF_PATH={MSV_PATCH_DIFF_PATH}", flush=True)
    if VULCAN_OUTPUT_DIR is None:
        print("[ERROR] VULCAN_OUTPUT_DIR is not set!!", file=sys.stderr, flush=True)
        exit(1)
    if VULCAN_TARGET is None:
        print("[ERROR] VULCAN_TARGET is not set!!", file=sys.stderr, flush=True)
        exit(1)
    if MSV_PATCH_DIFF_PATH is None:
        print("[ERROR] MSV_PATCH_DIFF_PATH is not set!!", file=sys.stderr, flush=True)
        exit(1)


def _preset():
    os.makedirs(VULCAN_OUTPUT_DIR, exist_ok=True)


def _gen_info_json():
    repo = Repo(VULCAN_TARGET)
    repo_git = repo.git
    os.chdir(VULCAN_TARGET)
    json_data = dict()
    json_data["snippets"] = []
    for p in os.listdir(MSV_PATCH_DIFF_PATH):
        p_path = os.path.join(MSV_PATCH_DIFF_PATH, p)
        print(f"[DEBUG] {p_path}", flush=True)

        os.system(f"patch -p0 < {p_path}")
        applied_path = ""
        for item in repo.index.diff(None):
            applied_path = item.a_path
            print(f"[DEBUG] applied {item.a_path}", flush=True)

        data = dict()
        data["id"] = p
        data["line"] = -1
        with open(p_path) as f:
            text = f.read()
            for diff in whatthepatch.parse_patch(text):
                if data["line"] != -1:
                    break
                for c in diff.changes:
                    if c[0] is not None and c[1] is None:
                        data["line"] = c[0]
                        break
                    if c[0] is None and c[1] is not None:
                        data["line"] = c[1]
                        break
        with open(f"{os.path.join(VULCAN_TARGET, applied_path)}") as f:
            data["lines"] = f.readlines()
        json_data["snippets"].append(data)
        repo_git.checkout(".")
    with open(os.path.join(VULCAN_OUTPUT_DIR, "patch.json"), "w", ) as json_file:
        json.dump(json_data, json_file)
    return json_data


def create_common_parser():
    parser = argparse.ArgumentParser()
    return parser


def create_parser():
    parser = create_common_parser()
    parser.add_argument(
        "--host",
        dest="host",
        action="store",
        default="xxx.xxx.xxx.xxx",
        help="set host to connect"
    )
    parser.add_argument(
        "--port",
        dest="port",
        action="store",
        default="xxxx",
        help="set port to connect"
    )
    return parser


def request_validation(args, snippets):
    url = f"http://{args.host}:{args.port}"
    try:
        response = requests.post(
            url=url,
            json=snippets
        )
    except Exception as e:
        print(f"[ERROR] {type(e)}, {e}, {e.__traceback__}")
        return None

    if response.status_code == 200:
        json_path = os.path.join(VALIDATION_REPORT_DIR, "validation_ai.json")
        with open(json_path, "w") as json_file:
            json.dump(response.json(), json_file)
        print(f"[INFO] Received patch validation data in {json_path}.", flush=True)
    else:
        print("[ERROR] Failed to validate.", flush=True)


class AIValidatorClient(ValidatorClient):
    def request(self, args):
        check_environments()
        parser = create_parser()
        args = parser.parse_args(sys.argv[1:])
        _preset()
        json_data = _gen_info_json()
        request_validation(args, json_data)
