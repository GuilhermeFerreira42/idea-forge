import sys
import os

# Add src to path
sys.path.append(os.path.abspath("idea-forge"))

try:
    from src.core.sectional_generator import NEXUS_FINAL_PASSES, SectionPass
    
    section_counts = {}
    for p in NEXUS_FINAL_PASSES:
        for s in p.sections:
            section_counts[s] = section_counts.get(s, 0) + 1
            
    duplicates = {s: count for s, count in section_counts.items() if count > 1}
    print(f"Duplicates: {duplicates}")
    
    for i, p in enumerate(NEXUS_FINAL_PASSES):
        print(f"Pass {i}: {p.pass_id} - {p.sections}")

except Exception as e:
    print(f"Error: {e}")
