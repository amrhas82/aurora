#!/bin/bash
# Remove all old marker decorators except ml, slow, real_api

for marker in unit integration e2e performance critical safety cli mcp soar core fast; do
  echo "Removing @pytest.mark.$marker..."
  find tests/ -name "*.py" -type f -exec sed -i "/^[[:space:]]*@pytest\.mark\.$marker[[:space:]]*$/d" {} \;
done

echo "Done!"
