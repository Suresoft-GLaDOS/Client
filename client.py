import argparse
import json
import requests
import sys
import os
import zipfile


VULCAN_OUTPUT_DIR = os.getenv("VULCAN_OUTPUT_DIR", "./")


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
        "--ip",
        dest="ip",
        action="store",
        default="xxx.xxx.xxx.xxx",
        help="set ip to connect"
    )
    parser.add_argument(
        "--port",
        dest="port",
        action="store",
        default="1179",
        help="set port to connect"
    )
    parser.add_argument(
        "--meta",
        dest="meta",
        action="store",
        help="set absolute file path to upload"
    )
    parser.add_argument(
        "--upload",
        dest="upload",
        action="store_true",
        default=True,
        help="upload file"
    )
    return parser


def request_file_upload(args):
    vulcan_output_directory = os.getenv("VULCAN_OUTPUT_DIR", None)
    if vulcan_output_directory:
        zip_target = _gen_zip(vulcan_output_directory)
        files = {"file": open(zip_target, "rb")}
        p = vulcan_output_directory.split("/")
        project = {"project": f"{p[-3]}-{p[-2]}-{p[-1]}"}
    else:
        files = {"file": open(args.meta, "rb")}
        project = {"project": args.project}
    upload_response = requests.post(
        url=f"http://{args.ip}:{args.port}/uploadFile",
        data=project,
        files=files
    )
    return upload_response


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])
    print("Requested patch validation...")
    response = request_file_upload(args)
    if response.json()["status"]:
        json_path = os.path.join(VULCAN_OUTPUT_DIR, "validation.json")
        with open(json_path, "w") as json_file:
            json.dump(response.json()["data"], json_file)
        print(f"Received patch validation data in {json_path}.")
    else:
        print("Failed to validate.")
