#!/bin/bash
# Ontology v1.0 Seeding - Complete Setup Script
# This script demonstrates the setup and usage of the ontology seeding system

set -e

PROJECT_ROOT="/Users/monikap/Downloads/my-curriculum-engine"
ONTOLOGY_DIR="$PROJECT_ROOT/packages/ontology/v1.0"

echo "=========================================================================="
echo "Ontology v1.0 Seeding System - Complete Setup"
echo "=========================================================================="
echo ""

# Check that files exist
echo "✓ Checking created files..."
echo ""

FILES=(
  "$ONTOLOGY_DIR/pillars.json"
  "$ONTOLOGY_DIR/skills.json"
  "$ONTOLOGY_DIR/indicators.json"
  "$ONTOLOGY_DIR/README.md"
  "$PROJECT_ROOT/apps/api/app/schemas/ontology_seed.py"
  "$PROJECT_ROOT/apps/api/app/services/seed_ontology_v1.py"
  "$PROJECT_ROOT/apps/api/app/services/__main__.py"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✓ $file"
  else
    echo "  ✗ $file (MISSING)"
  fi
done

echo ""
echo "=========================================================================="
echo "File Summary"
echo "=========================================================================="
echo ""

cat << 'EOF'
📁 packages/ontology/v1.0/
   ├── pillars.json          [EMPTY] - Populate with pillar definitions
   ├── skills.json           [EMPTY] - Populate with skill definitions
   ├── indicators.json       [EMPTY] - Populate with indicator keywords
   └── README.md             [CREATED] - Full documentation

📁 apps/api/app/schemas/
   └── ontology_seed.py      [CREATED] - Pydantic validation schemas
       ├── PillarSeedSchema
       ├── SkillSeedSchema
       └── IndicatorSeedSchema

📁 apps/api/app/services/
   ├── seed_ontology_v1.py   [CREATED] - Main seed service (559 lines)
   │   ├── _load_json_file()
   │   ├── _load_and_validate_pillars()
   │   ├── _load_and_validate_skills()
   │   ├── _load_and_validate_indicators()
   │   ├── _upsert_ontology_version()
   │   ├── _upsert_pillars()
   │   ├── _upsert_skills()
   │   ├── _upsert_indicators()
   │   ├── seed_ontology_v1_0()  [Main function]
   │   └── main()                [CLI entry point]
   │
   └── __main__.py           [CREATED] - CLI module support

📄 Root level documentation:
   ├── ONTOLOGY_SEEDING.md    [CREATED] - Implementation details
   └── packages/ontology/QUICKSTART.md [CREATED] - Quick start guide
EOF

echo ""
echo "=========================================================================="
echo "Next Steps"
echo "=========================================================================="
echo ""

cat << 'EOF'
1. POPULATE JSON FILES
   Edit the empty JSON files in packages/ontology/v1.0/ with your data.
   See QUICKSTART.md for sample data.

2. RUN SEED SCRIPT
   cd /Users/monikap/Downloads/my-curriculum-engine/apps/api
   conda run -n curriculum-engine python -m app.services.seed_ontology_v1

3. VERIFY IN DATABASE
   psql curriculum_engine -c "SELECT * FROM ontology_versions WHERE version_label='v1.0';"

4. START ANALYZING
   Use the ontology to analyze curriculum via /api/v1/analyze endpoint
EOF

echo ""
echo "=========================================================================="
echo "✅ Setup Complete!"
echo "=========================================================================="
echo ""
echo "Documentation:"
echo "  • Full guide: ONTOLOGY_SEEDING.md (repo root)"
echo "  • Quick start: packages/ontology/QUICKSTART.md"
echo "  • JSON schema: packages/ontology/v1.0/README.md"
echo ""
