#!/bin/bash

# Define mappings (old name to new name)
declare -a mappings=(
  "email_analyzer:classifier"
  "product_resolver:stockkeeper"
  "order_processor:fulfiller"
  "inquiry_responder:advisor"
  "response_composer:composer"
)

# Directories to search
dirs=("src" "docs" "notebooks" "tests" "tools")

# Process each mapping
for mapping in "${mappings[@]}"; do
  IFS=':' read -r old_name new_name <<< "$mapping"
  
  echo "Finding files with '$old_name' in their name..."
  
  # Find and process each file with the old name in its path
  for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
      echo "Searching in $dir..."
      
      # Find files with old_name in their path (excluding directories)
      files=$(find "$dir" -type f -path "*$old_name*" | sort)
      
      # Rename each file
      for file in $files; do
        # Create the new filename by replacing old_name with new_name
        new_file=$(echo "$file" | sed "s/$old_name/$new_name/g")
        
        # If the filename actually changed
        if [ "$file" != "$new_file" ]; then
          # Make sure the destination directory exists
          mkdir -p "$(dirname "$new_file")"
          
          echo "  Renaming: $file -> $new_file"
          mv "$file" "$new_file"
        fi
      done
      
      # Now handle directories (from deepest to shallowest to avoid path conflicts)
      dirs_to_rename=$(find "$dir" -type d -path "*$old_name*" | sort -r)
      
      for directory in $dirs_to_rename; do
        # Create the new directory name by replacing old_name with new_name
        new_directory=$(echo "$directory" | sed "s/$old_name/$new_name/g")
        
        # If the directory name actually changed
        if [ "$directory" != "$new_directory" ]; then
          # Check if directory still exists (might have been moved already as part of parent move)
          if [ -d "$directory" ]; then
            echo "  Renaming directory: $directory -> $new_directory"
            
            # Make sure the destination directory parent exists
            mkdir -p "$(dirname "$new_directory")"
            
            # Move the directory
            mv "$directory" "$new_directory"
          fi
        fi
      done
    else
      echo "Directory $dir does not exist, skipping."
    fi
  done
done

echo "File renaming complete!" 