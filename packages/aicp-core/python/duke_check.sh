#!/bin/bash
# Check what files actually exist in duke_checkpoints/

echo "📁 Listing all files in duke_checkpoints/"
echo "============================================================"
ls -lah duke_checkpoints/

echo ""
echo "🔍 Looking for pickle files..."
echo "============================================================"
find duke_checkpoints/ -name "*.pkl" -o -name "*.pth"

echo ""
echo "📊 File details:"
echo "============================================================"
for file in duke_checkpoints/*; do
    if [ -f "$file" ]; then
        echo "  $(basename $file): $(wc -c < $file) bytes"
    fi
done