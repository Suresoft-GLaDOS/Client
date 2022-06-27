import clients
import collections
import json
import os
import shutil
import sys

VULCAN_OUTPUT_DIR = os.getenv("VULCAN_OUTPUT_DIR", None)
VALIDATOR = os.getenv("VALIDATOR", None)
VALIDATION_REPORT_DIR = os.path.join(VULCAN_OUTPUT_DIR, "validation")
REPORT_FILE = os.path.join(VALIDATION_REPORT_DIR, "validation.json")


def check_environments():
    print(f"[INFO] VULCAN_OUTPUT_DIR={VULCAN_OUTPUT_DIR}", flush=True)
    print(f"[INFO] VALIDATOR={VALIDATOR}", flush=True)
    if VULCAN_OUTPUT_DIR is None:
        print("[ERROR] VULCAN_OUTPUT_DIR is not set!!", file=sys.stderr, flush=True)
        exit(1)
    if VALIDATOR is None:
        print("[ERROR] VALIDATOR is not set!!", file=sys.stderr, flush=True)
        exit(1)


def _preset():
    os.makedirs(VALIDATION_REPORT_DIR, exist_ok=True)
    if os.path.exists(REPORT_FILE):
        os.remove(REPORT_FILE)


def _assemble_rank():
    v_list = os.listdir(VALIDATION_REPORT_DIR)
    if len(v_list) == 1:
        shutil.copyfile(
            os.path.join(VALIDATION_REPORT_DIR, v_list[0]),
            os.path.join(VALIDATION_REPORT_DIR, "validation.json")
        )
        return

    assembled_rank = collections.defaultdict(lambda: 0)
    for f in v_list:
        if f == "validation.json":
            continue
        f_full_path = os.path.join(VALIDATION_REPORT_DIR, f)
        with open(f_full_path) as json_file:
            json_data = json.load(json_file)
        weight = 0.4 if "ct" in f else 1

        for i, d in enumerate(json_data["results"]):
            assembled_rank[d["id"]] += (i+1) * weight

    rank_data = []
    for k, v in assembled_rank.items():
        rank_data.append({
            "id": k,
            "score": v
        })
    with open(REPORT_FILE, "w") as json_file:
        json.dump({
            "results": sorted(rank_data, key=lambda k: k["score"])
        }, json_file)


if __name__ == "__main__":
    _preset()
    check_environments()
    print(f"[INFO] VALIDATOR={VALIDATOR}", flush=True)
    args = sys.argv[1:]
    if VALIDATOR == "No":
        print("[INFO] Do not validation", flush=True)
        exit()

    if VALIDATOR == "CT":
        clients.ct_client.TesterValidatorClient().request(args)
    elif VALIDATOR == "AI":
        clients.ai_client.AIValidatorClient().request(args)
    elif VALIDATOR == "All":
        clients.ct_client.TesterValidatorClient().request(args)
        clients.ai_client.AIValidatorClient().request(args)
    else:
        print("[ERROR] VALIDATOR is invalid", flush=True)
        exit(1)

    _assemble_rank()
