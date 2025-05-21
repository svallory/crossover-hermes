#!/bin/bash

# Define mappings (old name to new name)
declare -a mappings=(
  # "email_analyzer:classifier"
  # "EMAIL_ANALYZER:CLASSIFIER"
  # "EmailAnalyzer:Classifier"
  "\\.analyze_email:.agent"

  # "inquiry_responder:advisor"
  # "INQUIRY_RESPONDER:ADVISOR"
  # "InquiryResponder:Advisor"
  "\\.respond_to_inquiry:.agent"

  # "order_processor:fulfiller"
  # "ORDER_PROCESSOR:FULFILLER"
  # "OrderProcessor:Fulfiller"
  "\\.process_order:.agent"

  # "product_resolver:stockkeeper"
  # "PRODUCT_RESOLVER:STOCKKEEPER"
  # "ProductResolver:Stockkeeper"
  "\\.resolve_products:.agent"

  # "response_composer:composer"
  # "RESPONSE_COMPOSER:COMPOSER"
  # "ResponseComposer:Composer"
  "\\.compose_response:.agent"

  "from hermes:from src.hermes"
)

# The directories to search in
dirs=("src" "docs" "notebooks" "tests" "tools")

# Process each mapping
for mapping in "${mappings[@]}"; do
  IFS=':' read -r old_name new_name <<< "$mapping"
  
  echo "Renaming '$old_name' to '$new_name'..."
  
  # Find all files containing the old name and perform replacement
  for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
      echo "Searching in $dir..."
      
      # Find all files containing the old name
      files=$(grep -l "$old_name" $dir --include="*.py" --include="*.md" --include="*.ipynb" --include="*.json" -r)
      
      # Replace the old name with the new name in each file
      for file in $files; do
        echo "  Replacing in $file"
        sed -i "" "s/$old_name/$new_name/g" "$file"
      done
    else
      echo "Directory $dir does not exist, skipping."
    fi
  done
done

echo "Renaming complete!" 