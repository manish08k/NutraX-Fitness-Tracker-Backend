"""
Run this once after first deployment to seed the exercise library.
Usage: python scripts/seed_exercises.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings

EXERCISES = [
    # ── CHEST ─────────────────────────────────────────────────────
    {"name": "Barbell Bench Press", "muscle_group": "chest", "category": "strength", "equipment": "barbell", "difficulty": "intermediate",
     "description": "The king of chest exercises. Lie on a flat bench and press a barbell from chest level to full arm extension.",
     "instructions": ["Lie flat on bench, feet on floor", "Grip bar slightly wider than shoulder-width", "Lower bar to mid-chest under control", "Press explosively back to start", "Keep shoulder blades retracted throughout"],
     "tips": ["Don't bounce the bar off your chest", "Keep your back slightly arched — not flat", "Drive feet into the floor for stability"]},
    {"name": "Incline Dumbbell Press", "muscle_group": "chest", "category": "strength", "equipment": "dumbbell", "difficulty": "beginner",
     "description": "Targets the upper chest. Set bench to 30-45 degrees.",
     "instructions": ["Set bench to 30-45°", "Hold dumbbells at shoulder level", "Press up and slightly inward", "Lower slowly to starting position"],
     "tips": ["Don't go too steep — 45° max for chest focus", "Touch dumbbells at top without locking out"]},
    {"name": "Push-Up", "muscle_group": "chest", "category": "calisthenics", "equipment": "none", "difficulty": "beginner",
     "description": "Fundamental bodyweight chest exercise.",
     "instructions": ["Start in plank position, hands shoulder-width apart", "Lower chest to 1 inch from floor", "Push back up to start", "Keep core tight throughout"],
     "tips": ["Don't let hips sag or pike up", "Full range of motion — chest almost touching floor"]},
    {"name": "Cable Flye", "muscle_group": "chest", "category": "strength", "equipment": "cable machine", "difficulty": "intermediate",
     "description": "Isolation exercise for chest. Great for the mind-muscle connection.",
     "instructions": ["Set pulleys to shoulder height", "Stand in middle, slight forward lean", "Bring handles together in arc motion", "Slowly return to start"],
     "tips": ["Slight bend in elbow throughout", "Focus on squeezing the chest at peak contraction"]},

    # ── BACK ──────────────────────────────────────────────────────
    {"name": "Pull-Up", "muscle_group": "back", "category": "calisthenics", "equipment": "pull-up bar", "difficulty": "intermediate",
     "description": "Best bodyweight back exercise. Builds lat width and grip strength.",
     "instructions": ["Hang from bar, hands slightly wider than shoulders", "Pull chest to bar", "Lower slowly — full dead hang at bottom", "Cross feet for stability"],
     "tips": ["Don't kip unless training for CrossFit", "Scapular retraction before pulling"]},
    {"name": "Barbell Deadlift", "muscle_group": "back", "category": "strength", "equipment": "barbell", "difficulty": "advanced",
     "description": "The ultimate compound movement. Works entire posterior chain.",
     "instructions": ["Stand with mid-foot under bar", "Grip just outside legs", "Chest up, hips hinge down", "Push floor away — bar stays close to body", "Lock out hips and knees at top"],
     "tips": ["Never round your lower back", "Bar should drag up your shins (wear long socks)", "Brace your core like you're about to get punched"]},
    {"name": "Bent-Over Row", "muscle_group": "back", "category": "strength", "equipment": "barbell", "difficulty": "intermediate",
     "description": "Key compound row for back thickness.",
     "instructions": ["Hinge at hips, back parallel to floor", "Pull bar to lower chest/upper abdomen", "Lower with control", "Keep elbows close to body"],
     "tips": ["Don't use momentum — control the weight", "Squeeze shoulder blades together at top"]},
    {"name": "Lat Pulldown", "muscle_group": "back", "category": "strength", "equipment": "cable machine", "difficulty": "beginner",
     "description": "Machine alternative to pull-ups. Great for beginners building lat strength.",
     "instructions": ["Grip bar wider than shoulders", "Lean back slightly", "Pull bar to upper chest", "Slowly return to start — full stretch"],
     "tips": ["Don't pull behind neck — causes injury", "Lead with elbows, not hands"]},

    # ── SHOULDERS ─────────────────────────────────────────────────
    {"name": "Overhead Press", "muscle_group": "shoulders", "category": "strength", "equipment": "barbell", "difficulty": "intermediate",
     "description": "Compound shoulder builder. Also works triceps and upper back.",
     "instructions": ["Bar at upper chest, grip slightly wider than shoulder", "Press straight up — bar passes face", "Lock out at top", "Lower to clavicle level"],
     "tips": ["Squeeze glutes and brace core — protects lower back", "Don't press in front — press straight up"]},
    {"name": "Lateral Raise", "muscle_group": "shoulders", "category": "strength", "equipment": "dumbbell", "difficulty": "beginner",
     "description": "Isolation for the medial (side) deltoid — key for shoulder width.",
     "instructions": ["Hold dumbbells at sides", "Raise arms to shoulder level", "Lead with elbows, not wrists", "Slowly lower to start"],
     "tips": ["Use lighter weight than you think", "Slight forward lean isolates medial delt better", "Don't shrug at the top"]},

    # ── BICEPS ────────────────────────────────────────────────────
    {"name": "Barbell Curl", "muscle_group": "biceps", "category": "strength", "equipment": "barbell", "difficulty": "beginner",
     "description": "Classic bicep builder. More weight than dumbbells due to bilateral loading.",
     "instructions": ["Stand holding bar at hip level, underhand grip", "Curl to shoulder level", "Squeeze at top", "Lower slowly to full extension"],
     "tips": ["Don't swing — use strict form", "Full extension at bottom for full ROM"]},
    {"name": "Hammer Curl", "muscle_group": "biceps", "category": "strength", "equipment": "dumbbell", "difficulty": "beginner",
     "description": "Works brachialis and brachioradialis in addition to biceps.",
     "instructions": ["Hold dumbbells neutral grip (palms facing each other)", "Curl up keeping neutral grip", "Lower slowly"],
     "tips": ["Great for forearm development too", "Alternate arms or do both simultaneously"]},

    # ── TRICEPS ───────────────────────────────────────────────────
    {"name": "Close-Grip Bench Press", "muscle_group": "triceps", "category": "strength", "equipment": "barbell", "difficulty": "intermediate",
     "description": "Best mass-builder for triceps. Compound movement.",
     "instructions": ["Grip bar shoulder-width (not too narrow)", "Lower bar to lower chest", "Elbows stay close to body", "Press to full lockout"],
     "tips": ["Don't go too narrow — strains wrists", "Full lockout to maximally work triceps"]},
    {"name": "Tricep Pushdown", "muscle_group": "triceps", "category": "strength", "equipment": "cable machine", "difficulty": "beginner",
     "description": "Isolation exercise using cable machine.",
     "instructions": ["Stand facing cable, grip rope/bar at chest", "Push down to full extension", "Slowly return — don't let elbows flare"],
     "tips": ["Keep elbows pinned to sides", "Squeeze at full lockout for peak contraction"]},

    # ── CORE ──────────────────────────────────────────────────────
    {"name": "Plank", "muscle_group": "core", "category": "calisthenics", "equipment": "none", "difficulty": "beginner",
     "description": "Fundamental core stability exercise.",
     "instructions": ["Forearms on floor, elbows under shoulders", "Body in straight line from head to heels", "Hold position — breathe normally"],
     "tips": ["Don't hold breath", "Squeeze glutes and quads", "Don't let hips sag or pike"]},
    {"name": "Cable Crunch", "muscle_group": "core", "category": "strength", "equipment": "cable machine", "difficulty": "beginner",
     "description": "Weighted ab exercise. Allows progressive overload on abs.",
     "instructions": ["Kneel facing cable, hold rope at head level", "Crunch down, bringing elbows to knees", "Squeeze abs at bottom", "Slowly return to start"],
     "tips": ["Movement comes from abs, not hip flexors", "Keep hips stationary"]},

    # ── QUADS ─────────────────────────────────────────────────────
    {"name": "Barbell Back Squat", "muscle_group": "quads", "category": "strength", "equipment": "barbell", "difficulty": "advanced",
     "description": "King of all exercises. Primary quad builder, also works glutes and hamstrings.",
     "instructions": ["Bar on upper traps, feet shoulder-width", "Break at hips and knees simultaneously", "Squat until thighs parallel or below", "Drive through heels to stand"],
     "tips": ["Knees track over toes — don't cave inward", "Keep chest up and back straight", "Breathe in on way down, out on way up"]},
    {"name": "Leg Press", "muscle_group": "quads", "category": "strength", "equipment": "leg press machine", "difficulty": "beginner",
     "description": "Machine squat alternative. Allows heavy loading with less technique demand.",
     "instructions": ["Feet shoulder-width on platform", "Lower until 90° knee angle", "Press through heels to start", "Don't lock knees at top"],
     "tips": ["Never lock out knees fully", "Foot position changes emphasis: high=glutes, low=quads"]},
    {"name": "Leg Extension", "muscle_group": "quads", "category": "strength", "equipment": "leg extension machine", "difficulty": "beginner",
     "description": "Isolation exercise for the quadriceps.",
     "instructions": ["Sit in machine, pad on lower shin", "Extend legs to full lockout", "Squeeze quads at top", "Slowly lower"],
     "tips": ["Full extension for full quad activation", "Pause at top for extra burn"]},

    # ── HAMSTRINGS ────────────────────────────────────────────────
    {"name": "Romanian Deadlift", "muscle_group": "hamstrings", "category": "strength", "equipment": "barbell", "difficulty": "intermediate",
     "description": "Best hamstring builder. Hip hinge movement.",
     "instructions": ["Hold bar at hips, slight knee bend", "Hinge at hips — bar slides down thighs", "Feel hamstring stretch", "Drive hips forward to stand"],
     "tips": ["Don't round lower back", "Feel the stretch — go as far as flexibility allows", "Keep bar close to legs"]},
    {"name": "Leg Curl", "muscle_group": "hamstrings", "category": "strength", "equipment": "leg curl machine", "difficulty": "beginner",
     "description": "Isolation for hamstrings. Use lying or seated machine.",
     "instructions": ["Lie face down, pad above ankles", "Curl heels toward glutes", "Squeeze hamstrings at top", "Lower slowly to full extension"],
     "tips": ["Full range of motion", "Don't use momentum — slow and controlled"]},

    # ── GLUTES ────────────────────────────────────────────────────
    {"name": "Hip Thrust", "muscle_group": "glutes", "category": "strength", "equipment": "barbell", "difficulty": "intermediate",
     "description": "Best glute isolation exercise. Allows heavy loading.",
     "instructions": ["Shoulders on bench, bar across hips", "Drive hips up until parallel", "Squeeze glutes hard at top", "Lower under control"],
     "tips": ["Full extension at top — don't cut the range short", "Keep chin tucked to avoid hyperextending neck"]},

    # ── CARDIO ────────────────────────────────────────────────────
    {"name": "Running", "muscle_group": "cardio", "category": "cardio", "equipment": "none", "difficulty": "beginner",
     "description": "Classic cardiovascular exercise. Great for endurance and calorie burn.",
     "instructions": ["Land midfoot, not heel", "Slight forward lean", "Arms swing forward-back (not across body)", "Breathe rhythmically"],
     "tips": ["Start slow and build pace", "Warm up with 5 min walk first", "Run 3x/week max when starting out"]},
    {"name": "Jump Rope", "muscle_group": "cardio", "category": "cardio", "equipment": "jump rope", "difficulty": "beginner",
     "description": "High calorie-burn, portable cardio. Improves coordination and footwork.",
     "instructions": ["Small jumps — just enough to clear rope", "Wrists do the rotation, not arms", "Land on balls of feet", "Keep elbows close to body"],
     "tips": ["Start with 30 sec on / 30 sec off intervals", "Great for HIIT — 10 min burns ~100 calories"]},

    # ── FULL BODY ─────────────────────────────────────────────────
    {"name": "Burpee", "muscle_group": "full_body", "category": "plyometric", "equipment": "none", "difficulty": "intermediate",
     "description": "Full-body conditioning exercise. High calorie burn in short time.",
     "instructions": ["Stand → squat down, hands on floor", "Jump feet back to push-up position", "Do push-up (optional)", "Jump feet to hands", "Explode up with jump and clap"],
     "tips": ["Scale by removing jump or push-up", "Great for HIIT and fat loss circuits"]},
    {"name": "Kettlebell Swing", "muscle_group": "full_body", "category": "strength", "equipment": "kettlebell", "difficulty": "intermediate",
     "description": "Explosive hip hinge. Works posterior chain and conditions the cardiovascular system.",
     "instructions": ["Hike kettlebell back between legs", "Drive hips forward explosively", "Bell floats to shoulder height", "Control descent — hike back again"],
     "tips": ["Power comes from hips, not arms", "Keep back flat throughout", "Don't squat it — it's a hip hinge"]},
]


async def seed():
    from app.db.postgres import AsyncSessionLocal, init_db, Base, engine
    from app.models.workout import Exercise
    from sqlalchemy import select
    import uuid

    print("🌱 Seeding exercise library...")
    await init_db()

    async with AsyncSessionLocal() as db:
        for ex_data in EXERCISES:
            # Check if exists
            result = await db.execute(
                select(Exercise).where(Exercise.name == ex_data["name"])
            )
            if result.scalar_one_or_none():
                print(f"  ⏭  Skipping {ex_data['name']} (already exists)")
                continue

            exercise = Exercise(
                id=str(uuid.uuid4()),
                name=ex_data["name"],
                muscle_group=ex_data["muscle_group"],
                category=ex_data["category"],
                equipment=ex_data.get("equipment"),
                difficulty=ex_data.get("difficulty"),
                description=ex_data.get("description"),
                instructions=ex_data.get("instructions"),
                tips=ex_data.get("tips"),
                is_custom=False,
            )
            db.add(exercise)
            print(f"  ✅ {ex_data['name']}")

        await db.commit()

    print(f"\n✅ Seeded {len(EXERCISES)} exercises!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())
