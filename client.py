import clients
import os
import sys

VALIDATOR = os.getenv("VALIDATOR", None)

if __name__ == "__main__":
    print(f"[INFO] VALIDATOR={VALIDATOR}", flush=True)
    args = sys.argv[1:]
    if VALIDATOR == "CT":
        clients.ct_client.TesterValidatorClient().request(args)
    elif VALIDATOR == "AI":
        clients.ai_client.AIValidatorClient().request(args)
    elif VALIDATOR == "All":
        clients.ct_client.TesterValidatorClient().request(args)
        clients.ai_client.AIValidatorClient().request(args)
    elif VALIDATOR == "No":
        pass
    else:
        print("[ERROR] VALIDATOR is invalid", flush=True)
