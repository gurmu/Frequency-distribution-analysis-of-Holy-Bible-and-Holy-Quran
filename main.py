# main.py
from skill_client import get_skills

if __name__ == "__main__":
    skills = get_skills()
    if skills:
        print("\n=== Skills Data ===")
        print(skills)
    else:
        print("No skills returned.")