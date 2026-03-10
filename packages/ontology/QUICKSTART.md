# Quick Start: Populate and Seed Ontology

This guide shows you how to populate the JSON files with sample data and run the seed script.

## Sample Data

### 1. Populate pillars.json

```bash
cat > packages/ontology/v1.0/pillars.json << 'EOF'
[
  {
    "pillar_code": "P2",
    "name": "Analysis & Analytical Thinking",
    "description": "Students demonstrate the ability to analyze information, break down complex concepts, and evaluate evidence systematically.",
    "boundaries": "K-12, All subjects"
  },
  {
    "pillar_code": "P3",
    "name": "Critical Thinking & Problem Solving",
    "description": "Students apply critical thinking skills to solve problems, make decisions, and develop innovative solutions.",
    "boundaries": "K-12, All subjects"
  },
  {
    "pillar_code": "P1",
    "name": "Body and Health Intelligence",
    "description": "Students develop foundational knowledge and habits related to nutrition, physical activity, sleep, and personal wellness that support learning and long-term health.",
    "boundaries": "K-12, All subjects"
  }
]
EOF
```

### 2. Populate skills.json

```bash
cat > packages/ontology/v1.0/skills.json << 'EOF'
[
  {
    "pillar_code": "P2",
    "skill_code": "P2-S1",
    "name": "Breaking Down Complex Information",
    "description": "Ability to decompose complex ideas, texts, or problems into component parts for deeper understanding."
  },
  {
    "pillar_code": "P2",
    "skill_code": "P2-S2",
    "name": "Comparing & Evaluating Evidence",
    "description": "Ability to compare different viewpoints, evaluate evidence quality, and assess credibility."
  },
  {
    "pillar_code": "P3",
    "skill_code": "P3-S1",
    "name": "Problem Identification & Definition",
    "description": "Ability to identify, define, and articulate problems clearly before attempting solutions."
  },
  {
    "pillar_code": "P3",
    "skill_code": "P3-S2",
    "name": "Solution Development & Decision Making",
    "description": "Ability to develop multiple solutions, evaluate alternatives, and make informed decisions."
  },
  {
    "pillar_code": "P1",
    "skill_code": "P1-S1",
    "name": "Nutrition Foundations",
    "description": "Understanding basic nutrients, balanced meals, and how food impacts energy, focus, and mood."
  },
  {
    "pillar_code": "P1",
    "skill_code": "P1-S2",
    "name": "Daily Movement Habits",
    "description": "Practicing regular movement and exercise; understanding its role in focus, mood, and overall health."
  }
]
EOF
```

### 3. Populate indicators.json

```bash
cat > packages/ontology/v1.0/indicators.json << 'EOF'
[
  {
    "skill_code": "P2-S1",
    "indicator_type": "keyword",
    "indicator_text": "analyze, break down, decompose, identify parts, component, structure, element, examine, dissect, outline",
    "weight": 1.0
  },
  {
    "skill_code": "P2-S2",
    "indicator_type": "keyword",
    "indicator_text": "compare, contrast, evaluate, assess, judge, credibility, evidence, quality, reliable, source, validity",
    "weight": 1.0
  },
  {
    "skill_code": "P3-S1",
    "indicator_type": "keyword",
    "indicator_text": "problem, identify, define, issue, challenge, recognize, articulate, state, describe, frame",
    "weight": 1.0
  },
  {
    "skill_code": "P3-S2",
    "indicator_type": "keyword",
    "indicator_text": "solution, develop, create, alternative, option, strategy, decision, choose, select, plan, approach",
    "weight": 1.0
  },
  {
    "skill_code": "P1-S1",
    "indicator_type": "keyword",
    "indicator_text": "nutrition, food, healthy, balanced, nutrients, meal, diet, energy, food choices, eating habits",
    "weight": 1.0
  },
  {
    "skill_code": "P1-S2",
    "indicator_type": "keyword",
    "indicator_text": "movement, exercise, physical activity, fitness, stretching, activity, motion, sports, movement breaks",
    "weight": 1.0
  }
]
EOF
```

## Run the Seed Script

From the `apps/api/` directory:

```bash
cd /Users/monikap/Downloads/my-curriculum-engine/apps/api

# Using conda environment
conda run -n curriculum-engine python -m app.services.seed_ontology_v1
```

## Expected Output

```
======================================================================
✅ ONTOLOGY SEEDED SUCCESSFULLY
======================================================================

Version:     v1.0
Pillars:     3
Skills:      6
Indicators:  6

The ontology is now active and ready for curriculum analysis.
```

## Verify in Database

```bash
# From your PostgreSQL client
psql curriculum_engine

-- Check ontology version
SELECT id, version_label, status FROM ontology_versions WHERE version_label='v1.0';

-- Check pillars (replace <ontology_id> with the ID from above)
SELECT code, name FROM pillars WHERE ontology_version_id='<ontology_id>';

-- Check skills
SELECT code, name FROM skills ORDER BY code;

-- Check indicators
SELECT si.indicator_text, s.code as skill_code 
FROM skill_indicators si
JOIN skills s ON si.skill_id = s.id
ORDER BY s.code;
```

## Next: Use the Ontology

Now that the ontology is seeded, you can use it to analyze curriculum:

```bash
# Start the API server
cd /Users/monikap/Downloads/my-curriculum-engine/apps/api
uvicorn app.main:app --reload

# In another terminal, run an analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Plant Life Cycle Lesson",
    "curriculum_text": "Students analyze the life cycle of plants. They examine how plants grow from seeds, comparing growth under different light conditions.",
    "item_type": "lesson"
  }'
```

The response will include scores for P1, P2, and P3 based on how the curriculum text matches the indicators!

---

**Quick Start Date**: March 9, 2026  
**Version**: v1.0
