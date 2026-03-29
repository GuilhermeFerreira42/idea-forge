from src.debate.debate_state_tracker import DebateStateTracker

def test_repro():
    tracker = DebateStateTracker()
    critique = (
        "| ISS-01 | HIGH | SECURITY | X |\n"
        "| ISS-02 | LOW | CONSISTENCY | Y |\n"
    )
    new_ids = tracker.extract_issues_from_critique(critique, 1)
    print(f"New IDs: {new_ids}")
    
    defense = "## Pontos Aceitos\n- ISS-02: OK\n"
    resolved = tracker.extract_resolutions_from_defense(defense, 1)
    print(f"Resolved IDs: {resolved}")
    
    stats = tracker.get_stats()
    print(f"Stats: {stats}")
    
    if stats["total"] == 2 and stats["open"] == 1 and stats["resolved"] == 1:
        print("PASS")
    else:
        print("FAIL")

if __name__ == "__main__":
    test_repro()
