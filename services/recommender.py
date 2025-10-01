# Simple placeholder recommender. Replace with your ML pipeline.
def recommend_colleges(user_profile, colleges):
    # Very naive matching by budget and desired course keyword
    desired_course = (user_profile.get("desired_course") or "").lower()
    max_budget = user_profile.get("budget") or 10**12
    location_pref = (user_profile.get("location_pref") or "").lower()
    scored = []
    for c in colleges:
        score = 0
        if desired_course and any(desired_course in (course or '').lower() for course in c.get('courses', [])):
            score += 2
        if location_pref and location_pref in (c.get('location') or '').lower():
            score += 1
        fees = c.get("avg_fee") or 0
        if fees <= max_budget:
            score += 1
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:20]]
