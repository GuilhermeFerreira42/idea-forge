from src.debate.debate_state_tracker import DebateStateTracker

def test_sanity():
    tracker = DebateStateTracker()
    critique = (
        "## Issues Identificadas\\n"
        "| ID | Severidade | Categoria | Localização | Descrição | Sugestão |\\n"
        "|---|---|---|---|---|---|\\n"
        "| ISS-01 | HIGH | SECURITY | Seção Auth | Senha sem hash | Usar bcrypt |\\n"
    )
    # Re-normalize critique text because of write_to_file escaping
    critique = critique.replace("\\n", "\n")
    
    new_ids = tracker.extract_issues_from_critique(critique, round_num=1)
    print(f"New IDs: {new_ids}")
    if "ISS-01" in new_ids:
        print("PASS: Issue extracted correctly")
    else:
        print("FAIL: Issue NOT extracted")
        print(f"Critique text: {critique}")

if __name__ == "__main__":
    test_sanity()
