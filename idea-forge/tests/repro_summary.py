from src.debate.debate_state_tracker import DebateStateTracker

def test_repro_summary():
    tracker = DebateStateTracker()
    critique = "| ISS-01 | LOW | CONSISTENCY | Minor |\n"
    tracker.extract_issues_from_critique(critique, 1)
    
    defense = "## Pontos Aceitos\n- ISS-01: OK\n"
    resolved = tracker.extract_resolutions_from_defense(defense, 1)
    print(f"Resolved IDs: {resolved}")
    
    summary = tracker.get_consolidation_summary()
    print("SUMMARY OUTPUT:")
    print(summary)
    
    match1 = "Todos os issues foram resolvidos" in summary
    match2 = "✅ NÃO" in summary
    
    print(f"Match 1 (text): {match1}")
    print(f"Match 2 (NÃO): {match2}")
    
    if match1 and match2:
        print("PASS")
    else:
        print("FAIL")

if __name__ == "__main__":
    test_repro_summary()
