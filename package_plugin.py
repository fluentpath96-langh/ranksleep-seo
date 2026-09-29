"""
Utility script to package the WordPress plugin into a distributable instant-seo-agent.zip
"""

import os
import zipfile

def create_plugin_zip():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_src_dir = os.path.join(base_dir, "wordpress_plugin")
    output_zip = os.path.join(base_dir, "instant-seo-agent.zip")

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(plugin_src_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Store relative to 'instant-seo-agent' folder inside zip so WP extracts cleanly
                rel_path = os.path.relpath(file_path, plugin_src_dir)
                archive_name = os.path.join("instant-seo-agent", rel_path)
                zipf.write(file_path, archive_name)
    
    print(f"[OK] Plugin packaged successfully: {output_zip} ({os.path.getsize(output_zip)} bytes)")
    return output_zip

if __name__ == "__main__":
    create_plugin_zip()
