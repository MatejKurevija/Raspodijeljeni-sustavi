# main.py

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leader", action="store_true", help="Pokreni lidera (Flask).")
    parser.add_argument("--worker", type=str, help="Pokreni workera s ID-em.")
    args = parser.parse_args()

    if args.leader:
        # Uvezi i pozovi leader_process iz leader.py
        from leader import leader_process
        leader_process()  # starta Flask server i threadove
    elif args.worker:
        from worker import worker_process
        worker_id = args.worker
        print(f"[Main] Pokrećem worker s ID-jem: {worker_id}")
        worker_process(worker_id)
    else:
        print("Usage:\n"
              "  python main.py --leader\n"
              "  python main.py --worker <ID>")
        exit(1)

if __name__ == "__main__":
    main()
