import argparse
import json
import requests
import sys
import os
import zipfile

from clients.client_interface import ValidatorClient

CXBUILD_REPO = os.environ["CXBUILD_REPO"] = r"/home/workspace/cxbuild"

MSV_REPO = os.getenv("MSV_REPO", None)
VULCAN_OUTPUT_DIR = os.getenv("VULCAN_OUTPUT_DIR", None)
VULCAN_TARGET_WORKDIR = os.getenv("VULCAN_TARGET_WORKDIR", None)
VALIDATION_REPORT_DIR = os.path.join(VULCAN_OUTPUT_DIR, "validation")


def check_environments():
    print(f"[INFO] MSV_REPO={MSV_REPO}", flush=True)
    print(f"[INFO] CXBUILD_REPO={CXBUILD_REPO}", flush=True)
    print(f"[INFO] VULCAN_OUTPUT_DIR={VULCAN_OUTPUT_DIR}", flush=True)
    print(f"[INFO] VULCAN_TARGET_WORKDIR={VULCAN_TARGET_WORKDIR}", flush=True)
    if MSV_REPO is None:
        print("[ERROR] MSV_REPO is not set!!", file=sys.stderr, flush=True)
        exit(1)
    if CXBUILD_REPO is None:
        print("[ERROR] CXBUILD_REPO is not set!!", file=sys.stderr, flush=True)
        exit(1)
    if VULCAN_OUTPUT_DIR is None:
        print("[ERROR] VULCAN_OUTPUT_DIR is not set!!", file=sys.stderr, flush=True)
        exit(1)
    if VULCAN_TARGET_WORKDIR is None:
        print("[ERROR] VULCAN_TARGET_WORKDIR is not set!!", file=sys.stderr, flush=True)
        exit(1)


def _write_zf(zip_file, root_path, full_path):
    relative_path = os.path.relpath(full_path, root_path)
    zip_file.write(full_path, relative_path, zipfile.ZIP_DEFLATED)


def _gen_zip(output_dir):
    artifact_dir = os.path.join(output_dir, ".xdb", "artifacts")
    compile_commands_json = os.path.join(output_dir, ".xdb", "compile_commands.json")
    patch_info_json = os.path.join(output_dir, "msv-output", "msv-result-pass.json")
    zip_target = os.path.join(output_dir, "meta.zip")

    if os.path.exists(zip_target):
        os.remove(zip_target)

    with zipfile.ZipFile(zip_target, "a") as zf:
        for (path, directory, files) in os.walk(artifact_dir):
            for i in files:
                _write_zf(zf, artifact_dir, os.path.join(path, i))
        _write_zf(zf, os.path.dirname(compile_commands_json), compile_commands_json)
        _write_zf(zf, os.path.dirname(patch_info_json), patch_info_json)

    return zip_target


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


def run_cxbuild():
    """
    1. capture metaprogram
    """
    os.chdir(f"{VULCAN_TARGET_WORKDIR}/src")
    os.system("git clean -fdx")

    cxbuild_cmd = f"python3 {CXBUILD_REPO}/cxbuild.py capture" \
                  f" make LDFLAGS=\"-Wl,-rpath={MSV_REPO}/src/.libs -L{MSV_REPO}/src/.libs -ltest_runtime\""
    print(f"[DEBUG] {cxbuild_cmd}", flush=True)
    os.system(cxbuild_cmd)


def request_file_upload(args):
    zip_target = _gen_zip(VULCAN_OUTPUT_DIR)
    files = {"file": open(zip_target, "rb")}
    p = VULCAN_OUTPUT_DIR.split("/")
    project = {"project": f"{p[-3]}-{p[-2]}-{p[-1]}"}
    try:
        upload_response = requests.post(
            url=f"http://{args.host}:{args.port}/uploadFile",
            data=project,
            files=files
        )
    except Exception as e:
        print(f"[ERROR] {type(e)}, {e}, {e.__traceback__}")
        return None
    return upload_response


class TesterValidatorClient(ValidatorClient):
    def request(self, args):
        check_environments()
        run_cxbuild()
        parser = create_parser()
        args = parser.parse_args(sys.argv[1:])
        print("[INFO] Requested patch validation...", flush=True)
        response = request_file_upload(args)
        if response is None:
            pass
        elif response.json()["status"]:
            json_path = os.path.join(VALIDATION_REPORT_DIR, "validation_ct.json")
            with open(json_path, "w") as json_file:
                json.dump(response.json()["data"], json_file)
            print(f"[INFO] Received patch validation data in {json_path}.", flush=True)
        else:
            print(f"[DEBUG] {response.json()}")
            print("[ERROR] Failed to validate.", flush=True)
